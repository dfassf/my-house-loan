"""HF(한국주택금융공사) 홈페이지 크롤링.

금리 + 자격요건 + 우대조건 + 보도자료 모니터링.

디딤돌 상품안내: https://www.hf.go.kr/ko/sub01/sub01_02_01.do (자격요건)
디딤돌 금리안내: https://www.hf.go.kr/ko/sub01/sub01_02_03.do (금리)
보금자리론 상품안내: https://www.hf.go.kr/ko/sub01/sub01_01_01.do (자격요건)
보금자리론 금리안내: https://www.hf.go.kr/ko/sub01/sub01_01_04.do (금리)
보도자료: https://www.hf.go.kr/ko/sub05/sub05_04_05.do (변경 감지)
"""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from app.fetchers.base import BaseFetcher, FetchResult

logger = logging.getLogger(__name__)

_TIMEOUT = 15.0

# 디딤돌
_DIDIMDOL_RATE_URL = "https://www.hf.go.kr/ko/sub01/sub01_02_03.do"
_DIDIMDOL_PRODUCT_URL = "https://www.hf.go.kr/ko/sub01/sub01_02_01.do"

# 보금자리론
_BOGEUMJARI_RATE_URL = "https://www.hf.go.kr/ko/sub01/sub01_01_04.do"
_BOGEUMJARI_PRODUCT_URL = "https://www.hf.go.kr/ko/sub01/sub01_01_01.do"

# 보도자료
_NEWS_URL = "https://www.hf.go.kr/ko/sub05/sub05_04_05.do"

# 변경 감지 키워드
_ALERT_KEYWORDS = [
    "디딤돌", "보금자리", "금리", "대출한도", "소득기준", "자산기준",
    "LTV", "DSR", "주택가격", "순자산", "면적", "우대", "생애최초",
    "신혼", "다자녀", "자격요건", "개편", "개선", "인상", "인하", "변경",
]


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


# ── 금리 테이블 파싱 ────────────────────────────────────────


def _parse_rate_tables(html: str) -> dict[str, Any] | None:
    """HTML에서 금리 숫자를 추출."""
    rate_pattern = re.compile(r"(\d+\.\d{1,2})\s*%")
    rates = [float(m.group(1)) for m in rate_pattern.finditer(html)]

    if not rates:
        return None

    date_pattern = re.compile(r"(\d{4})[.\-년]\s*(\d{1,2})[.\-월]\s*(\d{1,2})")
    date_match = date_pattern.search(html)
    effective_date = ""
    if date_match:
        y, m, d = date_match.groups()
        effective_date = f"{y}-{int(m):02d}-{int(d):02d}"

    valid_rates = [r for r in rates if 0.5 <= r <= 10.0]

    return {
        "rates_found": valid_rates,
        "rate_min": min(valid_rates) if valid_rates else None,
        "rate_max": max(valid_rates) if valid_rates else None,
        "effective_date": effective_date,
        "raw_rate_count": len(valid_rates),
    }


# ── 자격요건 파싱 ──────────────────────────────────────────


def _parse_eligibility_page(html: str, product_id: str) -> dict[str, Any] | None:
    """상품안내 페이지에서 자격요건 추출.

    HF 페이지 구조가 바뀌면 파싱 실패할 수 있음 → None 반환.
    핵심 숫자(금액, 면적, 소득)는 정규식으로, 나머지는 키워드 기반.
    """
    result: dict[str, Any] = {}

    # ── 금액 패턴 (N억원, N천만원, N만원) ──
    amounts = _extract_amounts(html)
    if not amounts:
        return None

    result["amounts_found"] = amounts

    # ── 주택가격 상한 ──
    price_pattern = re.compile(r"주택가격[^0-9]*(\d[\d,.]*)\s*(억|만)")
    price_match = price_pattern.search(html)
    if price_match:
        result["max_housing_price"] = _amount_to_won(price_match.group(1), price_match.group(2))

    # ── 대출한도 ──
    loan_pattern = re.compile(r"대출한도[^0-9]*(\d[\d,.]*)\s*(억|만)")
    loan_match = loan_pattern.search(html)
    if loan_match:
        result["max_loan_amount"] = _amount_to_won(loan_match.group(1), loan_match.group(2))

    # ── 소득 기준 ──
    income_patterns = [
        re.compile(r"(?:연소득|부부합산[^0-9]*)(\d[\d,.]*)\s*(억|만)\s*원?\s*이하"),
        re.compile(r"소득[^0-9]*(\d[\d,.]*)\s*(억|만)\s*원?\s*이하"),
    ]
    for pat in income_patterns:
        match = pat.search(html)
        if match:
            result["max_income"] = _amount_to_won(match.group(1), match.group(2))
            break

    # ── 순자산 기준 ──
    asset_pattern = re.compile(r"순자산[^0-9]*(\d[\d,.]*)\s*(억|만)\s*원?\s*이하")
    asset_match = asset_pattern.search(html)
    if asset_match:
        result["max_net_assets"] = _amount_to_won(asset_match.group(1), asset_match.group(2))

    # ── 면적 ──
    area_pattern = re.compile(r"(\d{2,3})\s*[㎡m²]")
    area_matches = area_pattern.findall(html)
    if area_matches:
        areas = [int(a) for a in area_matches if 30 <= int(a) <= 200]
        if areas:
            result["max_area_m2"] = min(areas)
            if len(areas) > 1:
                result["max_area_m2_urban"] = max(areas)

    # ── LTV ──
    # "LTV 70%" 또는 "80%" 같이 LTV 문맥 근처의 퍼센트 추출
    ltv_section = re.search(r"LTV.{0,100}", html, re.DOTALL)
    if ltv_section:
        pct_pattern = re.compile(r"(\d{2,3})%")
        ltv_matches = pct_pattern.findall(ltv_section.group(0))
        if ltv_matches:
            result["ltv_values"] = [int(v) for v in ltv_matches if 30 <= int(v) <= 100]

    # ── 무주택 요건 ──
    result["requires_homeless"] = "무주택" in html

    # ── 신혼 관련 ──
    # "신혼 6억원 이하" 또는 "신혼가구 주택가격 6억원" 등 다양한 패턴
    newlywed_price_patterns = [
        re.compile(r"신혼[^0-9]*주택가격[^0-9]*(\d[\d,.]*)\s*(억|만)"),
        re.compile(r"신혼[^0-9]{0,5}(\d[\d,.]*)\s*(억)\s*원?\s*이하"),
    ]
    for pat in newlywed_price_patterns:
        nw_match = pat.search(html)
        if nw_match:
            result["max_housing_price_newlywed"] = _amount_to_won(nw_match.group(1), nw_match.group(2))
            break

    newlywed_income_patterns = [
        re.compile(r"신혼[^0-9]*소득[^0-9]*(\d[\d,.]*)\s*(억|만)"),
        re.compile(r"신혼[^0-9]{0,5}(\d[\d,.]*)\s*(만)\s*원?\s*이하"),
    ]
    for pat in newlywed_income_patterns:
        ni_match = pat.search(html)
        if ni_match:
            result["max_income_newlywed"] = _amount_to_won(ni_match.group(1), ni_match.group(2))
            break

    return result


def _extract_amounts(html: str) -> list[dict[str, Any]]:
    """HTML에서 금액 표현 추출 (N억원, N천만원 등)."""
    pattern = re.compile(r"(\d[\d,.]*)\s*(억|천만|만)\s*원")
    results = []
    for m in pattern.finditer(html):
        num_str = m.group(1).replace(",", "")
        unit = m.group(2)
        try:
            value = _amount_to_won(num_str, unit)
            results.append({"raw": m.group(0), "won": value})
        except ValueError:
            continue
    return results


def _amount_to_won(num_str: str, unit: str) -> int:
    """'5억' → 500000000, '7000만' → 70000000."""
    num = float(num_str.replace(",", ""))
    if unit == "억":
        return int(num * 100_000_000)
    if unit == "천만":
        return int(num * 10_000_000)
    if unit == "만":
        return int(num * 10_000)
    return int(num)


# ── 보도자료 파싱 ──────────────────────────────────────────


def _parse_news_list(html: str) -> list[dict[str, Any]] | None:
    """보도자료 목록에서 기사 제목 + ID 추출."""
    # HF 보도자료 목록의 링크 패턴
    # articleNo=599610 형태
    article_pattern = re.compile(
        r'articleNo=(\d+)[^>]*>([^<]+)<',
    )
    matches = article_pattern.findall(html)

    if not matches:
        # 다른 패턴 시도
        alt_pattern = re.compile(
            r'<a[^>]*href=["\'][^"\']*articleNo=(\d+)[^"\']*["\'][^>]*>\s*([^<]+?)\s*</a>',
        )
        matches = alt_pattern.findall(html)

    if not matches:
        return None

    articles: list[dict[str, Any]] = []
    for article_id, title in matches:
        title = title.strip()
        if not title:
            continue

        # 관련 키워드 매칭
        matched_keywords = [kw for kw in _ALERT_KEYWORDS if kw in title]
        is_relevant = len(matched_keywords) >= 2  # 2개 이상 키워드 매칭 시 관련 기사

        articles.append({
            "article_id": article_id,
            "title": title,
            "is_relevant": is_relevant,
            "keywords_matched": matched_keywords,
        })

    return articles
