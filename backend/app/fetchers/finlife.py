"""금감원 금융상품한눈에(finlife) API를 통한 은행 주담대 금리 수집.

엔드포인트: http://finlife.fss.or.kr/finlifeapi/mortgageLoanProductsSearch.json
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import settings
from app.fetchers.base import BaseFetcher, FetchResult

logger = logging.getLogger(__name__)

_TIMEOUT = 20.0
_URL = "https://finlife.fss.or.kr/finlifeapi/mortgageLoanProductsSearch.json"


class FinlifeFetcher(BaseFetcher):
    """은행 주택담보대출 금리 수집 (금감원 finlife)."""

    @property
    def source_name(self) -> str:
        return "finlife"

    async def fetch(self) -> FetchResult:
        key = settings.finlife_auth_key
        if not key:
            return self._fail("FINLIFE_AUTH_KEY 미설정")

        params: dict[str, str] = {
            "auth": key,
            "topFinGrpNo": "020000",  # 은행
            "pageNo": "1",
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(_URL, params=params)
                resp.raise_for_status()
                raw = resp.json()
        except httpx.HTTPError as e:
            return self._fail(f"HTTP 에러: {e}")
        except Exception as e:
            return self._fail(f"파싱 에러: {e}")

        parsed = _parse_finlife_response(raw)
        if parsed is None:
            return self._fail(f"응답 파싱 실패")

        return self._ok(data=parsed, raw=raw)


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _parse_finlife_response(raw: dict) -> dict | None:
    """finlife 응답에서 아파트 분할상환 금리 추출."""
    result = raw.get("result", {})
    base_list = result.get("baseList", [])
    option_list = result.get("optionList", [])

    if not option_list:
        return None

    # 상품코드 → 상품명/금융사명 매핑
    product_map: dict[str, dict[str, str]] = {}
    for item in base_list:
        code = item.get("fin_prdt_cd", "")
        product_map[code] = {
            "fin_co_nm": item.get("kor_co_nm", ""),
            "fin_prdt_nm": item.get("fin_prdt_nm", ""),
        }

    products: list[dict[str, Any]] = []
    rate_sum = 0.0
    rate_count = 0

    for opt in option_list:
        mrtg_type = opt.get("mrtg_type", "")         # A: 아파트
        rpay_type = opt.get("rpay_type", "")         # D: 분할상환
        lend_rate_type = opt.get("lend_rate_type", "")  # F: 고정, C: 변동

        rate_min = _safe_float(opt.get("lend_rate_min"))
        rate_max = _safe_float(opt.get("lend_rate_max"))
        rate_avg = _safe_float(opt.get("lend_rate_avg"))

        code = opt.get("fin_prdt_cd", "")
        info = product_map.get(code, {})

        product = {
            "fin_co_nm": info.get("fin_co_nm", ""),
            "fin_prdt_nm": info.get("fin_prdt_nm", ""),
            "mrtg_type": mrtg_type,
            "rpay_type": rpay_type,
            "lend_rate_type": lend_rate_type,
            "rate_min": rate_min,
            "rate_max": rate_max,
            "rate_avg": rate_avg,
        }
        products.append(product)

        # 아파트 분할상환 금리만 평균에 반영
        if mrtg_type == "A" and rpay_type == "D" and rate_avg is not None:
            rate_sum += rate_avg
            rate_count += 1

    dcls_month = ""
    if base_list:
        dcls_month = base_list[0].get("dcls_month", "")

    overall_avg = round(rate_sum / rate_count, 2) if rate_count > 0 else None

    return {
        "dcls_month": dcls_month,
        "products": products,
        "overall_avg_rate": overall_avg,
        "sample_count": rate_count,
    }
