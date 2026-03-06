"""HF(한국주택금융공사) 홈페이지 크롤링.

금리 + 자격요건 + 우대조건 + 보도자료 모니터링.

디딤돌 상품안내: https://www.hf.go.kr/ko/sub01/sub01_02_01.do (자격요건)
디딤돌 금리안내: https://www.hf.go.kr/ko/sub01/sub01_02_03.do (금리)
보금자리론 상품안내: https://www.hf.go.kr/ko/sub01/sub01_01_01.do (자격요건)
보금자리론 금리안내: https://www.hf.go.kr/ko/sub01/sub01_01_04.do (금리)
보도자료: https://www.hf.go.kr/ko/sub05/sub05_04_05.do (변경 감지)
"""

from __future__ import annotations

from typing import Any

import httpx

from app.fetchers.base import BaseFetcher, FetchResult
from app.fetchers.hf_parsers import (
    _amount_to_won,
    _parse_eligibility_page,
    _parse_news_list,
    _parse_rate_tables,
)

_TIMEOUT = 15.0

# 디딤돌
_DIDIMDOL_RATE_URL = "https://www.hf.go.kr/ko/sub01/sub01_02_03.do"
_DIDIMDOL_PRODUCT_URL = "https://www.hf.go.kr/ko/sub01/sub01_02_01.do"

# 보금자리론
_BOGEUMJARI_RATE_URL = "https://www.hf.go.kr/ko/sub01/sub01_01_04.do"
_BOGEUMJARI_PRODUCT_URL = "https://www.hf.go.kr/ko/sub01/sub01_01_01.do"

_NEWS_URL = "https://www.hf.go.kr/ko/sub05/sub05_04_05.do"


class HfDidimdolScraper(BaseFetcher):
    """HF 홈페이지에서 디딤돌대출 금리 + 자격요건 크롤링."""

    @property
    def source_name(self) -> str:
        return "hf_scrape_didimdol"

    async def fetch(self) -> FetchResult:
        async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
            # 금리 페이지 + 상품안내 페이지 병렬 수집
            try:
                rate_resp, product_resp = await _fetch_both(
                    client, _DIDIMDOL_RATE_URL, _DIDIMDOL_PRODUCT_URL,
                )
            except httpx.HTTPError as e:
                return self._fail(f"HTTP 에러: {e}")

        rate_info = _parse_rate_tables(rate_resp)
        eligibility_info = _parse_eligibility_page(product_resp, "didimdol")

        if not rate_info and not eligibility_info:
            return self._fail("HTML 파싱 실패: 금리/자격요건 모두 찾지 못함")

        data: dict[str, Any] = {"product_id": "didimdol"}
        if rate_info:
            data["rate_info"] = rate_info
        if eligibility_info:
            data["eligibility_info"] = eligibility_info

        return self._ok(data=data)


class HfBogeumjariScraper(BaseFetcher):
    """HF 홈페이지에서 보금자리론 금리 + 자격요건 크롤링."""

    @property
    def source_name(self) -> str:
        return "hf_scrape_bogeumjari"

    async def fetch(self) -> FetchResult:
        async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
            try:
                rate_resp, product_resp = await _fetch_both(
                    client, _BOGEUMJARI_RATE_URL, _BOGEUMJARI_PRODUCT_URL,
                )
            except httpx.HTTPError as e:
                return self._fail(f"HTTP 에러: {e}")

        rate_info = _parse_rate_tables(rate_resp)
        eligibility_info = _parse_eligibility_page(product_resp, "bogeumjari")

        if not rate_info and not eligibility_info:
            return self._fail("HTML 파싱 실패: 금리/자격요건 모두 찾지 못함")

        data: dict[str, Any] = {"product_id": "bogeumjari"}
        if rate_info:
            data["rate_info"] = rate_info
        if eligibility_info:
            data["eligibility_info"] = eligibility_info

        return self._ok(data=data)


class HfNewsScraper(BaseFetcher):
    """HF 보도자료 페이지 모니터링 — 정책 변경 감지."""

    @property
    def source_name(self) -> str:
        return "hf_news"

    async def fetch(self) -> FetchResult:
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
                resp = await client.get(_NEWS_URL)
                resp.raise_for_status()
                html = resp.text
        except httpx.HTTPError as e:
            return self._fail(f"HTTP 에러: {e}")

        articles = _parse_news_list(html)
        if articles is None:
            return self._fail("보도자료 파싱 실패")

        return self._ok(data={"articles": articles})


# ── 공통 유틸 ───────────────────────────────────────────────


async def _fetch_both(
    client: httpx.AsyncClient,
    url1: str,
    url2: str,
) -> tuple[str, str]:
    """두 페이지를 동시에 가져오기."""
    import asyncio

    async def _get(url: str) -> str:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.text

    r1, r2 = await asyncio.gather(_get(url1), _get(url2))
    return r1, r2
