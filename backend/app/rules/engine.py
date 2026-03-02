"""룰 엔진 오케스트레이터 — 정책대출 자격/금리 판정을 종합."""

from dataclasses import dataclass

from app.rules.eligibility import EligibilityResult, check_eligibility
from app.rules.product_loader import PolicyLoanData, load_bogeumjari, load_didimdol
from app.rules.rate_calculator import RateResult, calculate_rate
from app.schemas.loan_input import LoanSimulationRequest


@dataclass(frozen=True, slots=True)
class PolicyLoanOption:
    """자격 충족한 정책대출 옵션."""

    product_id: str
    product_name: str
    eligibility: EligibilityResult
    rate: RateResult
    max_loan_amount: int
    max_ltv_pct: float


@dataclass(frozen=True, slots=True)
class PolicyRejectionInfo:
    """정책대출 탈락 정보."""

    product_name: str
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PolicyEvaluationResult:
    """정책대출 평가 결과 (자격 충족 + 탈락 모두 포함)."""

    options: list[PolicyLoanOption]
    rejections: list[PolicyRejectionInfo]


def evaluate_policy_loans(request: LoanSimulationRequest) -> PolicyEvaluationResult:
    """모든 정책대출 상품에 대해 자격/금리 평가."""
    products: list[tuple[str, PolicyLoanData]] = [
        ("didimdol", load_didimdol()),
        ("bogeumjari", load_bogeumjari()),
    ]

    options: list[PolicyLoanOption] = []
    rejections: list[PolicyRejectionInfo] = []

    for _product_id, product in products:
        eligibility = check_eligibility(request, product)
        if not eligibility.eligible:
            rejections.append(PolicyRejectionInfo(
                product_name=product["product_name"],
                reasons=eligibility.reasons,
            ))
            continue

        rate = calculate_rate(request, product, request.loan_term_years)

        options.append(PolicyLoanOption(
            product_id=product["product_id"],
            product_name=product["product_name"],
            eligibility=eligibility,
            rate=rate,
            max_loan_amount=eligibility.max_loan_amount,
            max_ltv_pct=eligibility.max_ltv_pct,
        ))

    return PolicyEvaluationResult(options=options, rejections=rejections)
