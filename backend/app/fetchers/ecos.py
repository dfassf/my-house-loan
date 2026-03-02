"""한국은행 ECOS API를 통한 예금은행 주담대 평균금리 수집.

통계표코드: 121Y006 (예금은행 대출금리 - 신규취급액 기준)
항목코드: BECBLA0302 (주택담보대출)
주기: M (월간)
공표 시점: 익월 말 12:00
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import httpx

from app.config import settings
from app.fetchers.base import BaseFetcher, FetchResult

logger = logging.getLogger(__name__)

_TIMEOUT = 15.0
_BASE = "https://ecos.bok.or.kr/api/StatisticSearch"
_STAT_CODE = "121Y006"
_ITEM_CODE = "BECBLA0302"


class EcosFetcher(BaseFetcher):
    """예금은행 주택담보대출 가중평균 금리 수집 (ECOS)."""

    def __init__(self, months_back: int = 6) -> None:
        self._months_back = months_back

    @property
    def source_name(self) -> str:
        return "ecos"

    async def fetch(self) -> FetchResult:
        key = settings.ecos_api_key
        if not key:
            return self._fail("ECOS_API_KEY 미설정")

        now = datetime.now()
        # 최근 N개월 조회
        end_month = now.strftime("%Y%m")
        start_year = now.year
        start_month_num = now.month - self._months_back
        if start_month_num <= 0:
            start_year -= 1
            start_month_num += 12
        start_month = f"{start_year}{start_month_num:02d}"

        # ECOS REST URL: /{서비스명}/{인증키}/{요청유형}/{언어}/{시작}/{끝}/{통계표코드}/{주기}/{시작일}/{종료일}/{항목코드}
        # sample 키는 최대 10건, 정식 키는 넉넉하게 조회
        max_rows = 10 if key == "sample" else 100
        url = f"{_BASE}/{key}/json/kr/1/{max_rows}/{_STAT_CODE}/M/{start_month}/{end_month}/{_ITEM_CODE}"

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                raw = resp.json()
        except httpx.HTTPError as e:
            return self._fail(f"HTTP 에러: {e}")
        except Exception as e:
            return self._fail(f"파싱 에러: {e}")

        parsed = _parse_ecos_response(raw)
        if parsed is None:
            return self._fail(f"응답 파싱 실패")

        return self._ok(data=parsed, raw=raw)


def _parse_ecos_response(raw: dict) -> dict | None:
    """ECOS 응답에서 월별 금리 추출."""
    stat_search = raw.get("StatisticSearch")
    if not stat_search:
        return None

    rows: list[dict[str, Any]] = stat_search.get("row", [])
    if not rows:
        return None

    monthly_rates: list[dict[str, Any]] = []
    for row in rows:
        month = row.get("TIME", "")
        value = row.get("DATA_VALUE", "")
        try:
            rate = float(value)
        except (ValueError, TypeError):
            continue

        monthly_rates.append({
            "stat_month": month,
            "rate_value": rate,
        })

    if not monthly_rates:
        return None

    # 최신 월 금리
    latest = monthly_rates[-1]

    return {
        "monthly_rates": monthly_rates,
        "latest_month": latest["stat_month"],
        "latest_rate": latest["rate_value"],
    }
