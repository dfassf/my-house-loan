"""조합 최적화 — 정책대출 + 은행대출 조합을 생성하고 최적순으로 정렬."""

from dataclasses import dataclass

from app.calculator.bank_estimator import estimate_bank_rate
from app.calculator.repayment import (
    equal_principal,
    equal_principal_and_interest,
    graduated_payment,
)
from app.rules.engine import PolicyLoanOption, evaluate_policy_loans
from app.rules.regulation import calculate_dsr, calculate_regulation_limits
from app.schemas.loan_input import LoanSimulationRequest, RepaymentMethod
from app.schemas.loan_result import (
    CombinationResult,
    LoanProductResult,
    PolicyRejection,
    SimulationResponse,
)


def simulate(request: LoanSimulationRequest) -> SimulationResponse:
    """대출 시뮬레이션 전체 파이프라인."""
    # 1) 정책대출 평가
    evaluation = evaluate_policy_loans(request)
    policy_options = evaluation.options

    # 2) 은행 금리 추정
    bank_rate = estimate_bank_rate(request)

    # 3) 규제 한도 (은행 기준)
    bank_limits = calculate_regulation_limits(request, policy_exempt_dsr=False)

    # 4) 조합 생성
    combinations = _generate_combinations(request, policy_options, bank_rate, bank_limits)

    # 5) 정렬 (총 이자 기준 오름차순)
    combinations.sort(key=lambda c: c.total_interest)
    for i, combo in enumerate(combinations):
        combinations[i] = CombinationResult(
            rank=i + 1,
            products=combo.products,
            total_loan_amount=combo.total_loan_amount,
            total_monthly_payment=combo.total_monthly_payment,
            total_interest=combo.total_interest,
            total_payment=combo.total_payment,
            weighted_avg_rate=combo.weighted_avg_rate,
            dsr_ratio=combo.dsr_ratio,
            ltv_ratio=combo.ltv_ratio,
            label=combo.label,
        )

    # 6) 경고 메시지
    warnings: list[str] = []
    if not policy_options:
        warnings.append("조건에 맞는 정책대출 상품이 없어요.")
    if request.desired_amount > bank_limits.max_loanable and not policy_options:
        warnings.append(f"규제 한도 내 최대 대출 가능금액은 {bank_limits.max_loanable // 10000:,}만원이에요.")

    # 7) 정책대출 탈락 사유
    rejections = [
        PolicyRejection(product_name=r.product_name, reasons=list(r.reasons))
        for r in evaluation.rejections
    ]

    return SimulationResponse(
        combinations=combinations[:10],
        max_loanable=bank_limits.max_loanable,
        ltv_limit_pct=bank_limits.ltv_limit_pct,
        dsr_limit_pct=bank_limits.dsr_limit_pct,
        warnings=warnings,
        policy_rejections=rejections,
    )


def _generate_combinations(
    request: LoanSimulationRequest,
    policy_options: list[PolicyLoanOption],
    bank_rate: float,
    bank_limits,
) -> list[CombinationResult]:
    """정책대출 단독, 정책+은행 혼합, 은행 단독 조합을 생성."""
    combos: list[CombinationResult] = []
    desired = request.desired_amount
    housing_price = request.housing_price

    # A) 은행 단독
    bank_only_max = min(desired, bank_limits.max_loanable)
    if bank_only_max > 0:
        bank_product = _build_bank_product(request, bank_rate, bank_only_max)
        combo = _build_combination(request, [bank_product], housing_price, "은행대출 단독")
        if combo is not None:
            combos.append(combo)

    # B) 정책대출 단독 또는 정책 + 은행 혼합
    for option in policy_options:
        # 정책대출 최대 금액 (LTV 기반)
        policy_max_by_ltv = int(housing_price * option.max_ltv_pct / 100)
        policy_max = min(option.max_loan_amount, policy_max_by_ltv)

        # 정책대출 단독 (원하는 금액이 정책 한도 이내)
        if desired <= policy_max:
            policy_product = _build_policy_product(request, option, desired)
            combo = _build_combination(
                request, [policy_product], housing_price,
                f"{option.product_name} 단독",
            )
            if combo is not None:
                combos.append(combo)
        else:
            # 정책 최대 + 나머지 은행
            policy_amount = policy_max
            bank_remainder = desired - policy_amount
            bank_max = bank_limits.max_loanable

            if bank_remainder > bank_max:
                # 총액이 규제 초과 → 가능한 만큼만
                bank_remainder = bank_max
                total = policy_amount + bank_remainder
                if total < desired:
                    pass  # 희망액 미달이어도 조합은 제공

            if bank_remainder > 0:
                policy_product = _build_policy_product(request, option, policy_amount)
                bank_product = _build_bank_product(request, bank_rate, bank_remainder)
                combo = _build_combination(
                    request, [policy_product, bank_product], housing_price,
                    f"{option.product_name} + 은행",
                )
                if combo is not None:
                    combos.append(combo)

            # 정책 단독 (한도까지)
            if policy_amount > 0:
                policy_product = _build_policy_product(request, option, policy_amount)
                combo = _build_combination(
                    request, [policy_product], housing_price,
                    f"{option.product_name} (한도까지)",
                )
                if combo is not None:
                    combos.append(combo)

    return combos


def _build_policy_product(
    request: LoanSimulationRequest,
    option: PolicyLoanOption,
    amount: int,
) -> LoanProductResult:
    """정책대출 상품 결과 생성."""
    schedule = _calculate_repayment(
        amount, option.rate.final_rate_pct,
        request.loan_term_months, request.repayment_method,
    )

    return LoanProductResult(
        product_name=option.product_name,
        product_type="policy",
        loan_amount=amount,
        annual_rate_pct=option.rate.final_rate_pct,
        base_rate_pct=option.rate.base_rate_pct,
        discount_rate_pct=option.rate.discount_rate_pct,
        discount_details=list(option.rate.discount_details),
        monthly_payment=schedule.first_month_payment,
        total_interest=schedule.total_interest,
        total_payment=schedule.total_payment,
        loan_term_years=request.loan_term_years,
        repayment_method=request.repayment_method.value,
    )


def _build_bank_product(
    request: LoanSimulationRequest,
    bank_rate: float,
    amount: int,
) -> LoanProductResult:
    """은행대출 상품 결과 생성."""
    schedule = _calculate_repayment(
        amount, bank_rate,
        request.loan_term_months, request.repayment_method,
    )

    return LoanProductResult(
        product_name="시중은행 주택담보대출 (추정)",
        product_type="bank",
        loan_amount=amount,
        annual_rate_pct=bank_rate,
        base_rate_pct=bank_rate,
        discount_rate_pct=0,
        discount_details=[],
        monthly_payment=schedule.first_month_payment,
        total_interest=schedule.total_interest,
        total_payment=schedule.total_payment,
        loan_term_years=request.loan_term_years,
        repayment_method=request.repayment_method.value,
        eligibility_notes=["실제 금리는 은행별, 개인 심사에 따라 다릅니다"],
    )


def _build_combination(
    request: LoanSimulationRequest,
    products: list[LoanProductResult],
    housing_price: int,
    label: str,
) -> CombinationResult | None:
    """조합 결과 생성."""
    total_amount = sum(p.loan_amount for p in products)
    total_monthly = sum(p.monthly_payment for p in products)
    total_interest = sum(p.total_interest for p in products)
    total_payment = sum(p.total_payment for p in products)

    # 가중평균 금리
    if total_amount > 0:
        weighted_rate = sum(
            p.annual_rate_pct * p.loan_amount for p in products
        ) / total_amount
    else:
        weighted_rate = 0

    # LTV
    ltv = total_amount / housing_price * 100 if housing_price > 0 else 0

    # DSR
    annual_repayment = total_monthly * 12 + request.existing_debt_monthly * 12
    dsr = calculate_dsr(request.total_household_income, annual_repayment)

    return CombinationResult(
        rank=1,  # 정렬 후 재부여됨
        products=products,
        total_loan_amount=total_amount,
        total_monthly_payment=total_monthly,
        total_interest=total_interest,
        total_payment=total_payment,
        weighted_avg_rate=round(weighted_rate, 2),
        dsr_ratio=dsr,
        ltv_ratio=round(ltv, 2),
        label=label,
    )


def _calculate_repayment(
    principal: int,
    annual_rate_pct: float,
    months: int,
    method: RepaymentMethod,
):
    """상환 방식에 따른 스케줄 계산."""
    if method == RepaymentMethod.EQUAL_PRINCIPAL:
        return equal_principal(principal, annual_rate_pct, months)
    elif method == RepaymentMethod.GRADUATED:
        return graduated_payment(principal, annual_rate_pct, months)
    else:
        return equal_principal_and_interest(principal, annual_rate_pct, months)
