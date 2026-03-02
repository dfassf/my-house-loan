"""data.go.kr 공공데이터 API를 통한 정책대출 금리 수집.

디딤돌대출: http://apis.data.go.kr/B551408/didimdol-loan-rate/didimdol-info
보금자리론: http://apis.data.go.kr/B551408/u-loan-rate/uloan-info
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings
from app.fetchers.base import BaseFetcher, FetchResult

logger = logging.getLogger(__name__)

_TIMEOUT = 15.0
_BASE = "https://apis.data.go.kr/B551408"


class DidimdolFetcher(BaseFetcher):
    """디딤돌대출 금리 수집 (data.go.kr)."""

    @property
    def source_name(self) -> str:
        return "data_go_kr_didimdol"

    async def fetch(self) -> FetchResult:
        key = settings.data_go_kr_service_key
        if not key:
            return self._fail("DATA_GO_KR_SERVICE_KEY 미설정")

        url = f"{_BASE}/didimdol-loan-rate/didimdol-info"
        params: dict[str, str] = {
            "serviceKey": key,
            "pageNo": "1",
            "numOfRows": "10",
            "dataType": "JSON",
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                raw = resp.json()
        except httpx.HTTPError as e:
            return self._fail(f"HTTP 에러: {e}")
        except Exception as e:
            return self._fail(f"파싱 에러: {e}")

        parsed = _parse_didimdol_response(raw)
        if parsed is None:
            return self._fail(f"응답 파싱 실패: {raw}")

        return self._ok(data=parsed, raw=raw)


class BogeumjariFetcher(BaseFetcher):
    """보금자리론 금리 수집 (data.go.kr)."""

    @property
    def source_name(self) -> str:
        return "data_go_kr_bogeumjari"

    async def fetch(self) -> FetchResult:
        key = settings.data_go_kr_service_key
        if not key:
            return self._fail("DATA_GO_KR_SERVICE_KEY 미설정")

        url = f"{_BASE}/u-loan-rate/uloan-info"
        params: dict[str, str] = {
            "serviceKey": key,
            "pageNo": "1",
            "numOfRows": "10",
            "dataType": "JSON",
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                raw = resp.json()
        except httpx.HTTPError as e:
            return self._fail(f"HTTP 에러: {e}")
        except Exception as e:
            return self._fail(f"파싱 에러: {e}")

        parsed = _parse_bogeumjari_response(raw)
        if parsed is None:
            return self._fail(f"응답 파싱 실패: {raw}")

        return self._ok(data=parsed, raw=raw)


def _safe_float(value: Any) -> float | None:
    """문자열/숫자를 float로 변환. 실패 시 None."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _extract_items(raw: dict) -> list[dict] | None:
    """data.go.kr 공통 응답에서 items 추출.

    두 가지 형태 지원:
    1) {"response": {"body": {"items": {"item": [...]}}}}  (구형)
    2) {"body": {"item": {...}}}  (신형 — 단일 dict)
    """
    try:
        # 신형: body.item (단일 dict)
        body = raw.get("body")
        if body is not None:
            item = body.get("item")
            if isinstance(item, dict):
                return [item]
            if isinstance(item, list):
                return item

        # 구형: response.body.items.item
        resp_body = raw.get("response", {}).get("body", {})
        items = resp_body.get("items", {})
        if isinstance(items, dict):
            result = items.get("item", [])
            if isinstance(result, dict):
                return [result]
            return result
        if isinstance(items, list):
            return items
    except (AttributeError, KeyError):
        pass
    return None


def _parse_didimdol_response(raw: dict) -> dict | None:
    """디딤돌 API 응답 → income_rate_tiers 형태로 변환.

    실제 API 응답 (2026):
    {"body": {"item": {
        "interest_10y_2000": "2.85", "interest_15y_2000": "2.95", ...
        "interest_10y_4000": "3.20", ...
        "interest_10y_6000": "3.55", ...
        "applyDy": "20260301"
    }}}

    필드 패턴: interest_{기간}y_{소득구간(만원)}
    소득구간: 2000 → 2천만원 이하, 4000 → 4천만원 이하, 6000 → 6천만원 이하
    """
    items = _extract_items(raw)
    if not items:
        return None

    item = items[0]

    # ── 신형 응답: interest_{term}y_{income} 패턴 ──
    import re
    pattern = re.compile(r"interest_(\d+)y_(\d+)")

    # 소득구간별 금리 수집
    tier_map: dict[int, dict[str, Any]] = {}
    for key, value in item.items():
        m = pattern.match(key)
        if not m:
            continue
        term = int(m.group(1))
        income_level = int(m.group(2))  # 만원 단위 (2000 = 2천만)
        rate = _safe_float(value)
        if rate is None:
            continue

        if income_level not in tier_map:
            tier_map[income_level] = {"max_income": income_level * 10_000}
        tier_map[income_level][f"rate_{term}y"] = rate

    if tier_map:
        # 소득구간 오름차순 정렬
        tiers = [tier_map[k] for k in sorted(tier_map.keys())]

        effective_date = item.get("applyDy", "")
        if len(effective_date) == 8:
            effective_date = f"{effective_date[:4]}-{effective_date[4:6]}-{effective_date[6:]}"

        return {
            "income_rate_tiers": tiers,
            "effective_date": effective_date,
        }

    # ── 구형 응답 폴백: loanRate{N} 패턴 ──
    tiers_old: list[dict[str, Any]] = []
    effective_date = ""

    for it in items:
        rate_10 = _safe_float(it.get("loanRate10"))
        rate_15 = _safe_float(it.get("loanRate15"))
        rate_20 = _safe_float(it.get("loanRate20"))
        rate_30 = _safe_float(it.get("loanRate30"))
        max_income = _safe_float(it.get("incomeLevel"))

        if rate_10 is not None or rate_30 is not None:
            tier: dict[str, Any] = {}
            if max_income is not None:
                tier["max_income"] = int(max_income)
            if rate_10 is not None:
                tier["rate_10y"] = rate_10
            if rate_15 is not None:
                tier["rate_15y"] = rate_15
            if rate_20 is not None:
                tier["rate_20y"] = rate_20
            if rate_30 is not None:
                tier["rate_30y"] = rate_30
            tiers_old.append(tier)

        if not effective_date:
            effective_date = str(it.get("effectiveDate") or it.get("applyDate") or "")

    if not tiers_old:
        return None

    return {
        "income_rate_tiers": tiers_old,
        "effective_date": effective_date,
    }


def _parse_bogeumjari_response(raw: dict) -> dict | None:
    """보금자리론 API 응답 → income_rate_tiers 형태로 변환.

    실제 API 응답 (예상):
    {"body": {"item": {
        "interest_10y": "4.05", "interest_15y": "4.15",
        "interest_20y": "4.25", "interest_30y": "4.35",
        "interest_40y": "4.40", "interest_50y": "4.45",
        "applyDy": "20260301"
    }}}
    """
    items = _extract_items(raw)
    if not items:
        return None

    item = items[0] if items else {}

    # 신형: interest_{N}y 패턴
    tier: dict[str, Any] = {"max_income": 70_000_000}
    has_rate = False

    for term in [10, 15, 20, 30, 40, 50]:
        # 신형: interest_Ny / 구형: loanRateN
        val = _safe_float(
            item.get(f"interest_{term}y")
            or item.get(f"loanRate{term}")
        )
        if val is not None:
            tier[f"rate_{term}y"] = val
            has_rate = True

    if not has_rate:
        logger.info("[bogeumjari] 금리 파싱 실패, 원본: %s", item)
        return None

    effective_date = item.get("applyDy") or item.get("effectiveDate") or ""
    if len(effective_date) == 8:
        effective_date = f"{effective_date[:4]}-{effective_date[4:6]}-{effective_date[6:]}"

    return {
        "income_rate_tiers": [tier],
        "effective_date": effective_date,
    }
