"""정책대출 자격 판정 모듈."""

from dataclasses import dataclass, field

from app.rules.product_loader import PolicyLoanData
from app.schemas.loan_input import LoanSimulationRequest, MaritalStatus


@dataclass(frozen=True, slots=True)
class EligibilityResult:
    """자격 판정 결과."""

    eligible: bool
    product_id: str
    reasons: tuple[str, ...] = ()
    max_loan_amount: int = 0
    max_ltv_pct: float = 0


def check_eligibility(
    request: LoanSimulationRequest,
    product: PolicyLoanData,
) -> EligibilityResult:
    """사용자 조건과 정책대출 상품의 자격 요건을 비교."""
    product_id = product["product_id"]
    failures: list[str] = []

    # 무주택 요건
    if product.get("requires_homeless", False) and not request.is_homeless:
        failures.append("무주택자만 신청 가능")

    # 주택 가격 상한
    max_price = _get_max_housing_price(request, product)
    if request.housing_price > max_price:
        failures.append(f"주택 가격 초과 (상한: {max_price // 10000:,}만원)")

    # 소득 상한
    max_income = _get_max_income(request, product)
    if request.total_household_income > max_income:
        failures.append(f"소득 초과 (상한: {max_income // 10000:,}만원)")

    # 순자산 상한
    max_assets = product.get("max_net_assets", 0)
    if max_assets > 0 and request.net_assets > max_assets:
        failures.append(f"순자산 초과 (상한: {max_assets // 10000:,}만원)")

    # 전용면적 (도시 지역은 max_area_m2_urban 적용)
    max_area = product.get("max_area_m2_urban", product.get("max_area_m2", 85))
    if request.housing_area_m2 > max_area:
        failures.append(f"전용면적 초과 (상한: {max_area}m²)")

    # 대출 한도 계산
    max_loan = _get_max_loan_amount(request, product)
    max_ltv = _get_max_ltv(request, product)

    if failures:
        return EligibilityResult(
            eligible=False,
            product_id=product_id,
            reasons=tuple(failures),
            max_loan_amount=0,
            max_ltv_pct=0,
        )

    return EligibilityResult(
        eligible=True,
        product_id=product_id,
        reasons=(),
        max_loan_amount=max_loan,
        max_ltv_pct=max_ltv,
    )


def _get_max_housing_price(req: LoanSimulationRequest, product: PolicyLoanData) -> int:
    """신혼/다자녀 등 조건에 따른 주택 가격 상한. 가장 유리한 조건 적용."""
    base = product["max_housing_price"]
    candidates = [base]

    if req.marital_status == MaritalStatus.NEWLYWED:
        candidates.append(product.get("max_housing_price_newlywed", base))

    if req.num_children >= 2:
        candidates.append(product.get("max_housing_price_multi_child", base))

    return max(candidates)


def _get_max_income(req: LoanSimulationRequest, product: PolicyLoanData) -> int:
    """조건에 따른 소득 상한. 가장 유리한 조건 적용.

    디딤돌: 일반 6천만, 생애최초/2자녀+ 7천만, 신혼 8500만
    보금자리론: 일반 7천만, 신혼 8500만, 1자녀 8천만, 2자녀 9천만, 3자녀+ 1억
    """
    base = product["max_income"]
    candidates = [base]

    # 신혼
    if req.marital_status == MaritalStatus.NEWLYWED:
        candidates.append(product.get("max_income_newlywed", base))

    # 생애최초
    if req.is_first_time_buyer:
        candidates.append(product.get("max_income_first_time", base))

    # 자녀수별 (가장 높은 해당 구간)
    if req.num_children >= 3:
        candidates.append(product.get("max_income_3child", base))
    if req.num_children >= 2:
        candidates.append(product.get("max_income_2child", base))
        candidates.append(product.get("max_income_multi_child", base))
    if req.num_children >= 1:
        candidates.append(product.get("max_income_1child", base))

    return max(candidates)


def _get_max_loan_amount(req: LoanSimulationRequest, product: PolicyLoanData) -> int:
    """조건에 따른 최대 대출금액. 가장 유리한 조건 적용."""
    base = product["max_loan_amount"]
    candidates = [base]

    if req.marital_status == MaritalStatus.NEWLYWED:
        candidates.append(product.get("max_loan_amount_newlywed", base))

    if req.is_first_time_buyer:
        candidates.append(product.get("max_loan_amount_first_time", base))

    if req.num_children >= 2:
        candidates.append(product.get("max_loan_amount_multi_child", base))

    return max(candidates)


def _get_max_ltv(req: LoanSimulationRequest, product: PolicyLoanData) -> float:
    """조건에 따른 최대 LTV."""
    ltv = product.get("max_ltv_pct", 70)

    if req.is_first_time_buyer:
        ltv = max(ltv, product.get("max_ltv_pct_first_time", ltv))

    return ltv
