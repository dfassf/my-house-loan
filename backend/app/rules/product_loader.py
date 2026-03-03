"""대출 상품 룰 데이터 로딩 (인메모리 캐시 → JSON 폴백)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, TypedDict

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent / "data"


# ── TypedDict 정의 ──────────────────────────────────────────


class IncomeRateTierDict(TypedDict, total=False):
    max_income: int
    rate_10y: float
    rate_15y: float
    rate_20y: float
    rate_30y: float
    rate_40y: float
    rate_50y: float
    rate_fixed: float


class DiscountConditionDict(TypedDict):
    name: str
    discount_pct: float
    condition: str


class PolicyLoanData(TypedDict, total=False):
    product_id: str
    product_name: str
    product_type: str

    max_housing_price: int
    max_housing_price_newlywed: int
    max_income: int
    max_income_married: int
    max_income_newlywed: int
    max_net_assets: int
    requires_homeless: bool
    min_area_m2: float
    max_area_m2: float
    max_area_m2_urban: float

    max_loan_amount: int
    max_loan_amount_newlywed: int
    max_loan_amount_first_time: int
    max_ltv_pct: float
    max_ltv_pct_first_time: float

    income_rate_tiers: list[IncomeRateTierDict]
    newlywed_rate_tiers: list[IncomeRateTierDict]
    discount_conditions: list[DiscountConditionDict]
    max_total_discount: float
    min_rate_floor: float
    min_rate_floor_newlywed: float

    available_terms_years: list[int]
    available_repayment_methods: list[str]


class CreditAdjustmentDict(TypedDict):
    min_score: int
    max_score: int
    adjustment_pct: float


class BankAverageData(TypedDict, total=False):
    base_rates: dict[str, float | str]
    credit_adjustments: list[CreditAdjustmentDict]
    default_rate_key: str
    max_ltv_by_region: dict[str, int]


class LtvDsrData(TypedDict, total=False):
    ltv_limits: dict[str, dict[str, float | int | str] | int | str]
    dsr_limits: dict[str, float | int | str]
    policy_loan_overrides: dict[str, float | int | bool | str]


# ── JSON 파일 로딩 ──────────────────────────────────────────


def _load_json(filename: str) -> dict:
    path = DATA_DIR / filename
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_base_product_data(product_id: str) -> dict:
    """상품의 JSON 기본 데이터를 반환. admin 수동 수정 시 사용."""
    return _load_json(f"{product_id}.json")


# ── 2단계 로딩: 인메모리 캐시 → JSON 폴백 ────────────────────


_cache: dict[str, dict] = {}


def _load_policy_product(product_id: str, json_filename: str) -> PolicyLoanData:
    """정책대출 상품 데이터 로딩 (2단계 폴백).

    1. 인메모리 캐시에 데이터가 있으면 → JSON 기본값 위에 캐시 데이터를 병합
    2. 캐시가 없으면 → JSON 파일 그대로 사용
    """
    cache_key = product_id
    if cache_key in _cache:
        return _cache[cache_key]  # type: ignore[return-value]

    # JSON 기본 데이터 (전체 구조의 기본값)
    base_data = _load_json(json_filename)

    # 인메모리 캐시에서 병합 시도
    from app.cache import cache as mem_cache

    cached_data = mem_cache.get_product_data(product_id)
    if cached_data is not None:
        merged_count = 0
        for key, value in cached_data.items():
            if key.startswith("_"):
                continue  # 메타 필드 스킵
            if value is not None:
                base_data[key] = value
                merged_count += 1
        logger.info("[%s] 인메모리 캐시 적용 (%d개 필드 병합)", product_id, merged_count)

    _cache[cache_key] = base_data
    return base_data  # type: ignore[return-value]


def load_didimdol() -> PolicyLoanData:
    return _load_policy_product("didimdol", "didimdol.json")


def load_bogeumjari() -> PolicyLoanData:
    return _load_policy_product("bogeumjari", "bogeumjari.json")


def load_ltv_dsr() -> LtvDsrData:
    if "ltv_dsr" not in _cache:
        _cache["ltv_dsr"] = _load_json("ltv_dsr.json")
    return _cache["ltv_dsr"]  # type: ignore[return-value]


def load_bank_average() -> BankAverageData:
    if "bank_average" not in _cache:
        base_data = _load_json("bank_average.json")

        # 인메모리 캐시에서 최신 은행 평균금리가 있으면 variable 금리 오버라이드
        from app.cache import cache as mem_cache

        cached_avg = mem_cache.get_latest_avg_rate()
        if cached_avg is not None:
            base_data["base_rates"]["variable"] = cached_avg
            logger.info("[bank_average] 인메모리 평균금리 적용: %.2f%%", cached_avg)

        _cache["bank_average"] = base_data

    return _cache["bank_average"]  # type: ignore[return-value]


def clear_cache() -> None:
    """캐시 초기화. 금리 갱신 후 또는 테스트에서 사용."""
    _cache.clear()
