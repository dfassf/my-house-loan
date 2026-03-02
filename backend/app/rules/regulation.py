"""LTV/DSR 규제 필터 모듈.

10.15 부동산 대책 (2025.10.20 시행) 기준:
- 규제지역 (서울 + 수도권 일부): 무주택 LTV 40%, 생애최초 LTV 70%, 유주택자 0%
- 절대 한도: 15억 이하 6억, 15~25억 4억, 25억 초과 2억
- 스트레스 DSR: 대출금리 + 3.0%p 가산 (규제지역), +1.5%p (비규제)
"""

from dataclasses import dataclass

from app.rules.product_loader import load_ltv_dsr
from app.schemas.loan_input import LoanSimulationRequest, Region


@dataclass(frozen=True, slots=True)
class RegulationLimits:
    """규제 한도."""

    ltv_limit_pct: float
    dsr_limit_pct: float
    max_loan_by_ltv: int
    max_loan_by_dsr: int
    max_loanable: int
    notes: tuple[str, ...]


def calculate_regulation_limits(
    request: LoanSimulationRequest,
    policy_exempt_dsr: bool = False,
) -> RegulationLimits:
    """은행대출 기준 LTV/DSR 한도 계산."""
    data = load_ltv_dsr()
    notes: list[str] = []
    is_regulated = _is_regulated_zone(request.region)

    # LTV 한도
    ltv_pct = _get_ltv_limit(request, data, is_regulated)
    max_by_ltv = int(request.housing_price * ltv_pct / 100)

    # 절대 한도 적용 (규제지역)
    if is_regulated:
        absolute_cap = _get_absolute_cap(request.housing_price, data)
        if absolute_cap is not None and max_by_ltv > absolute_cap:
            max_by_ltv = absolute_cap
            notes.append(f"규제지역 대출 절대 한도 {absolute_cap // 100_000_000}억원 적용")

    if request.is_first_time_buyer:
        notes.append(f"생애최초 LTV {ltv_pct}% 적용")

    # DSR 한도
    dsr_limits = data.get("dsr_limits", {})
    dsr_pct = float(dsr_limits.get("default_pct", 40))

    if policy_exempt_dsr:
        max_by_dsr = max_by_ltv
        notes.append("정책대출 DSR 완화 적용")
    else:
        stress_add = _get_stress_rate(is_regulated, data)
        max_by_dsr = _calculate_max_by_dsr(request, dsr_pct, stress_add)
        if stress_add > 0:
            notes.append(f"스트레스 DSR +{stress_add}%p 가산 적용")

    max_loanable = min(max_by_ltv, max_by_dsr)

    return RegulationLimits(
        ltv_limit_pct=ltv_pct,
        dsr_limit_pct=dsr_pct,
        max_loan_by_ltv=max_by_ltv,
        max_loan_by_dsr=max_by_dsr,
        max_loanable=max_loanable,
        notes=tuple(notes),
    )


def calculate_dsr(
    annual_income: int,
    total_annual_repayment: int,
) -> float:
    """DSR 비율 계산 (%)."""
    if annual_income <= 0:
        return 100.0 if total_annual_repayment > 0 else 0.0
    return round(total_annual_repayment / annual_income * 100, 2)


def _is_regulated_zone(region: Region) -> bool:
    """규제지역 여부. 서울 + 수도권(경기/인천 일부)은 규제지역으로 처리."""
    return region in (Region.SEOUL, Region.METROPOLITAN)


def _get_ltv_limit(
    request: LoanSimulationRequest,
    data: dict,
    is_regulated: bool,
) -> float:
    """지역·주택유형에 따른 은행 LTV 한도."""
    if is_regulated:
        regulated = data.get("regulated_zones", {}).get("ltv", {})

        if not request.is_homeless:
            return float(regulated.get("homeowner", 0))

        if request.is_first_time_buyer:
            return float(regulated.get("homeless_first_time", 70))

        return float(regulated.get("homeless_general", 40))

    else:
        non_regulated = data.get("non_regulated_zones", {}).get("ltv", {})

        if request.is_first_time_buyer:
            return float(non_regulated.get("first_time", 80))

        return float(non_regulated.get("general", 70))


def _get_absolute_cap(housing_price: int, data: dict) -> int | None:
    """규제지역 주택 시가 구간별 절대 대출 한도."""
    caps = data.get("regulated_zones", {}).get("absolute_caps", {})
    if not caps:
        return None

    if housing_price <= 1_500_000_000:
        cap = caps.get("under_15억")
    elif housing_price <= 2_500_000_000:
        cap = caps.get("15억_to_25억")
    else:
        cap = caps.get("over_25억")

    return int(cap) if cap is not None else None


def _get_stress_rate(is_regulated: bool, data: dict) -> float:
    """스트레스 DSR 가산 금리."""
    dsr_limits = data.get("dsr_limits", {})
    if is_regulated:
        return float(dsr_limits.get("stress_rate_add_pct", 3.0))
    return float(dsr_limits.get("stress_rate_non_regulated_pct", 1.5))


def _calculate_max_by_dsr(
    request: LoanSimulationRequest,
    dsr_limit_pct: float,
    stress_add_pct: float = 0,
) -> int:
    """DSR 한도 내 최대 대출금액 추정.

    DSR = (기존상환 + 신규상환) / 연소득 <= limit
    → 신규 연 상환 가능 = 연소득 * limit% - 기존상환*12
    → 대출금액 ≈ 연 상환 가능 / (금리/100 + 1/기간) (원리금균등 근사)
    스트레스 DSR: 실제 금리 대신 (금리 + stress_add) 적용
    """
    annual_income = request.total_household_income
    if annual_income <= 0:
        return 0

    existing_annual = request.existing_debt_monthly * 12
    max_annual_repayment = int(annual_income * dsr_limit_pct / 100) - existing_annual

    if max_annual_repayment <= 0:
        return 0

    # 은행 평균 금리 ~4% + 스트레스 가산
    approx_rate = (4.0 + stress_add_pct) / 100
    approx_months = request.loan_term_months
    monthly_rate = approx_rate / 12

    if monthly_rate > 0 and approx_months > 0:
        factor = (1 + monthly_rate) ** approx_months
        max_monthly = max_annual_repayment / 12
        estimated = max_monthly * (factor - 1) / (monthly_rate * factor)
        return max(0, int(estimated))

    return max(0, max_annual_repayment * approx_months // 12)
