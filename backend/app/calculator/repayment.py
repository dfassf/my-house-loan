"""
상환 계산기 — 3가지 상환방식의 월별 상환 스케줄 계산.

모든 금액은 원(KRW) 단위, 금리는 연이율(%) 단위.
예: principal=300_000_000, annual_rate=3.5, months=360
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MonthlyPayment:
    """단일 월의 상환 내역."""

    month: int
    principal_payment: int  # 원금 상환분
    interest_payment: int  # 이자 상환분
    total_payment: int  # 월 납입금 (원금 + 이자)
    remaining_balance: int  # 잔여 원금


@dataclass(frozen=True, slots=True)
class RepaymentSchedule:
    """상환 스케줄 전체 요약."""

    method: str
    monthly_payments: tuple[MonthlyPayment, ...]
    total_interest: int  # 총 이자
    total_payment: int  # 총 납입금 (원금 + 이자)
    first_month_payment: int  # 첫 달 납입금
    last_month_payment: int  # 마지막 달 납입금
    max_month_payment: int  # 최대 월 납입금


def _monthly_rate(annual_rate_pct: float) -> float:
    """연이율(%)을 월이율(소수)로 변환."""
    return annual_rate_pct / 100 / 12


def equal_principal_and_interest(
    principal: int,
    annual_rate_pct: float,
    months: int,
) -> RepaymentSchedule:
    """
    원리금균등상환 (Equal Principal and Interest).

    매달 동일한 금액(원금+이자)을 납부.
    월납입금 = P * r * (1+r)^n / ((1+r)^n - 1)
    """
    if months <= 0:
        raise ValueError(f"상환 기간은 1개월 이상이어야 합니다: {months}")
    if principal <= 0:
        raise ValueError(f"대출 원금은 양수여야 합니다: {principal}")

    r = _monthly_rate(annual_rate_pct)
    payments: list[MonthlyPayment] = []
    remaining = principal

    if r == 0:
        # 무이자
        base_payment = principal // months
        for i in range(1, months + 1):
            p_pay = base_payment if i < months else remaining
            remaining -= p_pay
            payments.append(MonthlyPayment(
                month=i,
                principal_payment=p_pay,
                interest_payment=0,
                total_payment=p_pay,
                remaining_balance=remaining,
            ))
    else:
        # 원리금균등 공식
        factor = (1 + r) ** months
        fixed_payment = round(principal * r * factor / (factor - 1))

        for i in range(1, months + 1):
            interest = round(remaining * r)
            p_pay = fixed_payment - interest

            if i == months:
                # 마지막 달: 잔여 원금 전액 상환 (반올림 오차 보정)
                p_pay = remaining
                interest = round(remaining * r)

            remaining -= p_pay
            if remaining < 0:
                remaining = 0

            payments.append(MonthlyPayment(
                month=i,
                principal_payment=p_pay,
                interest_payment=interest,
                total_payment=p_pay + interest,
                remaining_balance=remaining,
            ))

    return _build_schedule("equal_principal_and_interest", payments)


def equal_principal(
    principal: int,
    annual_rate_pct: float,
    months: int,
) -> RepaymentSchedule:
    """
    원금균등상환 (Equal Principal).

    매달 동일한 원금을 상환하고, 이자는 잔여 원금에 대해 계산.
    월원금 = P / n
    월이자 = 잔여원금 * r
    """
    if months <= 0:
        raise ValueError(f"상환 기간은 1개월 이상이어야 합니다: {months}")
    if principal <= 0:
        raise ValueError(f"대출 원금은 양수여야 합니다: {principal}")

    r = _monthly_rate(annual_rate_pct)
    base_principal = principal // months
    payments: list[MonthlyPayment] = []
    remaining = principal

    for i in range(1, months + 1):
        interest = round(remaining * r)

        if i == months:
            p_pay = remaining
        else:
            p_pay = base_principal

        remaining -= p_pay
        if remaining < 0:
            remaining = 0

        payments.append(MonthlyPayment(
            month=i,
            principal_payment=p_pay,
            interest_payment=interest,
            total_payment=p_pay + interest,
            remaining_balance=remaining,
        ))

    return _build_schedule("equal_principal", payments)


def graduated_payment(
    principal: int,
    annual_rate_pct: float,
    months: int,
    graduation_period: int = 12,
    growth_rate_pct: float = 5.0,
) -> RepaymentSchedule:
    """
    채증식상환 (Graduated Payment).

    초기 납입금이 낮고, graduation_period마다 growth_rate_pct만큼 증가.
    초기 월납입금 = P * r / (1 - (1/(1+g))^(n/p) * 1/((1+r)^p))
    (단순화된 근사 방식 사용)

    실무에서는 주택도시기금 채증식이 10년 단위 1.5배 증가 등 다양한 변형 존재.
    여기서는 일반적인 graduated payment 방식으로 구현.
    """
    if months <= 0:
        raise ValueError(f"상환 기간은 1개월 이상이어야 합니다: {months}")
    if principal <= 0:
        raise ValueError(f"대출 원금은 양수여야 합니다: {principal}")
    if graduation_period <= 0:
        raise ValueError(f"증가 주기는 양수여야 합니다: {graduation_period}")

    r = _monthly_rate(annual_rate_pct)
    g = growth_rate_pct / 100  # 증가율 (소수)

    # 단계 수
    num_steps = (months + graduation_period - 1) // graduation_period

    if r == 0:
        # 무이자: 단순 균등 분할
        return equal_principal(principal, 0, months)

    # 초기 월납입금 계산 (뉴턴-랩슨 방식 대신 해석적 근사)
    # 각 단계의 월납입금: M_k = M_0 * (1+g)^k (k=0부터)
    # 총 상환금 = sum_k [ M_0*(1+g)^k * min(graduation_period, months - k*graduation_period) ]
    # 이것이 원금+이자 합계와 같아야 함

    # 먼저 원리금균등의 총 납입금으로 대략적인 총액 계산
    factor = (1 + r) ** months
    epi_monthly = principal * r * factor / (factor - 1)
    total_target = epi_monthly * months

    # 초기 월납입금 역산
    weight_sum = 0.0
    for k in range(num_steps):
        step_months = min(graduation_period, months - k * graduation_period)
        weight_sum += ((1 + g) ** k) * step_months

    initial_payment = total_target / weight_sum if weight_sum > 0 else epi_monthly

    # 스케줄 생성
    payments: list[MonthlyPayment] = []
    remaining = principal

    for i in range(1, months + 1):
        step_index = (i - 1) // graduation_period
        current_payment = round(initial_payment * ((1 + g) ** step_index))
        interest = round(remaining * r)

        if i == months:
            # 마지막 달: 잔여 원금 전액
            p_pay = remaining
            interest = round(remaining * r)
        else:
            p_pay = current_payment - interest
            if p_pay < 0:
                p_pay = 0  # 초기에는 이자만 낼 수 있음

        remaining -= p_pay
        if remaining < 0:
            remaining = 0

        payments.append(MonthlyPayment(
            month=i,
            principal_payment=p_pay,
            interest_payment=interest,
            total_payment=p_pay + interest,
            remaining_balance=remaining,
        ))

    return _build_schedule("graduated_payment", payments)


def _build_schedule(method: str, payments: list[MonthlyPayment]) -> RepaymentSchedule:
    """MonthlyPayment 리스트로부터 RepaymentSchedule 요약을 생성."""
    total_interest = sum(p.interest_payment for p in payments)
    total_payment = sum(p.total_payment for p in payments)

    return RepaymentSchedule(
        method=method,
        monthly_payments=tuple(payments),
        total_interest=total_interest,
        total_payment=total_payment,
        first_month_payment=payments[0].total_payment if payments else 0,
        last_month_payment=payments[-1].total_payment if payments else 0,
        max_month_payment=max((p.total_payment for p in payments), default=0),
    )
