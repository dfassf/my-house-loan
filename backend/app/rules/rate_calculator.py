"""정책대출 금리 계산 모듈 (기본 금리 + 우대 금리)."""

from dataclasses import dataclass

from app.rules.product_loader import PolicyLoanData
from app.schemas.loan_input import LoanSimulationRequest, MaritalStatus


@dataclass(frozen=True, slots=True)
class RateResult:
    """금리 계산 결과."""

    base_rate_pct: float
    discount_rate_pct: float
    final_rate_pct: float
    discount_details: tuple[str, ...]


def calculate_rate(
    request: LoanSimulationRequest,
    product: PolicyLoanData,
    loan_term_years: int,
) -> RateResult:
    """사용자 조건에 따라 금리를 계산."""
    base_rate = _get_base_rate(request, product, loan_term_years)
    discount, details = _get_discounts(request, product)

    max_discount = product.get("max_total_discount", 1.0)
    capped_discount = min(discount, max_discount)

    # 최저 금리 하한 적용
    if request.marital_status == MaritalStatus.NEWLYWED:
        floor = product.get("min_rate_floor_newlywed", 0)
    else:
        floor = product.get("min_rate_floor", 0)

    final_rate = max(floor, base_rate - capped_discount)

    return RateResult(
        base_rate_pct=base_rate,
        discount_rate_pct=capped_discount,
        final_rate_pct=round(final_rate, 2),
        discount_details=tuple(details),
    )


def _get_base_rate(
    request: LoanSimulationRequest,
    product: PolicyLoanData,
    loan_term_years: int,
) -> float:
    """소득 구간 + 대출 기간별 기본 금리."""
    income = request.total_household_income

    # 신혼 전용 금리 테이블이 있으면 우선 사용
    if (
        request.marital_status == MaritalStatus.NEWLYWED
        and "newlywed_rate_tiers" in product
    ):
        tiers = product["newlywed_rate_tiers"]
    else:
        tiers = product.get("income_rate_tiers", [])

    for tier in tiers:
        if income <= tier["max_income"]:
            # 보금자리론: 고정금리 (기간 무관)
            if "rate_fixed" in tier:
                return tier["rate_fixed"]

            # 디딤돌: 기간별 금리
            rate_key = f"rate_{loan_term_years}y"
            if rate_key in tier:
                return tier[rate_key]

            # 기간이 맞는 키가 없으면 가장 가까운 키
            available_keys = [k for k in tier if k.startswith("rate_") and k != "rate_fixed"]
            if available_keys:
                return tier[available_keys[-1]]

            return 3.0  # fallback

    # 소득이 모든 구간 초과 → 마지막 구간
    if tiers:
        last_tier = tiers[-1]
        if "rate_fixed" in last_tier:
            return last_tier["rate_fixed"]
        rate_key = f"rate_{loan_term_years}y"
        if rate_key in last_tier:
            return last_tier[rate_key]

    return 3.0  # fallback


def _get_discounts(
    request: LoanSimulationRequest,
    product: PolicyLoanData,
) -> tuple[float, list[str]]:
    """적용 가능한 우대 금리 합산."""
    conditions = product.get("discount_conditions", [])
    total_discount = 0.0
    details: list[str] = []

    for cond in conditions:
        name = cond["name"]
        discount = cond["discount_pct"]

        if name in ("전자계약", "전자약정등기"):
            # 전자계약/전자약정등기는 항상 적용 가정
            total_discount += discount
            details.append(f"{name} -{discount}%p")

        elif name == "신혼가구":
            if request.marital_status == MaritalStatus.NEWLYWED:
                total_discount += discount
                details.append(f"신혼가구 -{discount}%p")

        elif name == "다자녀3":
            if request.num_children >= 3:
                total_discount += discount
                details.append(f"다자녀(3+) -{discount}%p")

        elif name == "다자녀":
            if request.num_children == 2:
                total_discount += discount
                details.append(f"다자녀(2) -{discount}%p")

        elif name == "1자녀":
            if request.num_children == 1:
                total_discount += discount
                details.append(f"1자녀 -{discount}%p")

        elif name == "생애최초":
            if request.is_first_time_buyer:
                total_discount += discount
                details.append(f"생애최초 -{discount}%p")

        elif name == "한부모":
            # 한부모는 별도 입력 필드 없으므로 스킵
            pass

    return total_discount, details
