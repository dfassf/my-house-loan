"""상환 계산기 단위 테스트."""

import pytest

from app.calculator.repayment import (
    MonthlyPayment,
    RepaymentSchedule,
    equal_principal,
    equal_principal_and_interest,
    graduated_payment,
)


class TestEqualPrincipalAndInterest:
    """원리금균등상환 테스트."""

    def test_basic_case(self):
        """3억, 연 3.5%, 30년 기본 케이스."""
        result = equal_principal_and_interest(300_000_000, 3.5, 360)

        assert result.method == "equal_principal_and_interest"
        assert len(result.monthly_payments) == 360

        # 원리금균등: 매달 비슷한 금액 (첫 달 ≈ 마지막 달)
        first = result.monthly_payments[0]
        last = result.monthly_payments[-1]
        assert abs(first.total_payment - last.total_payment) < first.total_payment * 0.05

        # 총 납입금 > 원금
        assert result.total_payment > 300_000_000
        assert result.total_interest > 0

        # 마지막 달 잔여 원금 = 0
        assert last.remaining_balance == 0

    def test_known_value(self):
        """알려진 값 검증: 1억, 연 4%, 12개월."""
        result = equal_principal_and_interest(100_000_000, 4.0, 12)

        # 월납입금 ≈ 8,515,237원 (네이버 대출계산기 기준 ±1% 오차 허용)
        first_payment = result.first_month_payment
        assert 8_400_000 <= first_payment <= 8_600_000

        # 총 이자 ≈ 2,182,850원
        assert 2_000_000 <= result.total_interest <= 2_400_000

        # 마지막 잔액 = 0
        assert result.monthly_payments[-1].remaining_balance == 0

    def test_zero_rate(self):
        """무이자 대출."""
        result = equal_principal_and_interest(120_000_000, 0.0, 12)

        assert result.total_interest == 0
        assert result.total_payment == 120_000_000

        for p in result.monthly_payments:
            assert p.interest_payment == 0

    def test_short_term(self):
        """1개월 대출."""
        result = equal_principal_and_interest(10_000_000, 3.0, 1)

        assert len(result.monthly_payments) == 1
        p = result.monthly_payments[0]
        assert p.principal_payment == 10_000_000
        assert p.remaining_balance == 0

    def test_invalid_months(self):
        with pytest.raises(ValueError, match="1개월 이상"):
            equal_principal_and_interest(100_000_000, 3.0, 0)

    def test_invalid_principal(self):
        with pytest.raises(ValueError, match="양수"):
            equal_principal_and_interest(0, 3.0, 12)


class TestEqualPrincipal:
    """원금균등상환 테스트."""

    def test_basic_case(self):
        """3억, 연 3.5%, 30년 기본 케이스."""
        result = equal_principal(300_000_000, 3.5, 360)

        assert result.method == "equal_principal"
        assert len(result.monthly_payments) == 360

        # 원금균등: 첫 달 납입금 > 마지막 달 (이자가 감소하므로)
        first = result.monthly_payments[0]
        last = result.monthly_payments[-1]
        assert first.total_payment > last.total_payment

        # 매달 원금 상환분은 거의 동일
        mid = result.monthly_payments[180]
        assert abs(first.principal_payment - mid.principal_payment) <= 1

        # 마지막 잔액 = 0
        assert last.remaining_balance == 0

    def test_total_principal_equals_loan(self):
        """총 상환 원금 = 대출 원금."""
        result = equal_principal(200_000_000, 3.0, 240)

        total_principal = sum(p.principal_payment for p in result.monthly_payments)
        assert total_principal == 200_000_000

    def test_decreasing_payment(self):
        """월 납입금이 점차 감소."""
        result = equal_principal(100_000_000, 5.0, 120)

        for i in range(len(result.monthly_payments) - 1):
            assert result.monthly_payments[i].total_payment >= result.monthly_payments[i + 1].total_payment

    def test_zero_rate(self):
        """무이자."""
        result = equal_principal(120_000_000, 0.0, 12)
        assert result.total_interest == 0

    def test_interest_less_than_epi(self):
        """원금균등의 총 이자 < 원리금균등의 총 이자."""
        ep = equal_principal(300_000_000, 3.5, 360)
        epi = equal_principal_and_interest(300_000_000, 3.5, 360)

        assert ep.total_interest < epi.total_interest


class TestGraduatedPayment:
    """채증식상환 테스트."""

    def test_basic_case(self):
        """3억, 연 3.5%, 30년 기본 케이스."""
        result = graduated_payment(300_000_000, 3.5, 360)

        assert result.method == "graduated_payment"
        assert len(result.monthly_payments) == 360

        # 채증식: 첫 달 < 마지막 달
        first = result.monthly_payments[0]
        last = result.monthly_payments[-1]
        assert first.total_payment < last.total_payment

        # 마지막 잔액 = 0
        assert last.remaining_balance == 0

    def test_increasing_trend(self):
        """graduation_period마다 납입금 증가."""
        result = graduated_payment(200_000_000, 4.0, 240, graduation_period=12)

        # 1년차 첫 달 vs 2년차 첫 달
        year1_first = result.monthly_payments[0].total_payment
        year2_first = result.monthly_payments[12].total_payment
        assert year2_first > year1_first

    def test_zero_rate(self):
        """무이자시 원금균등과 동일하게 동작."""
        result = graduated_payment(120_000_000, 0.0, 12)
        assert result.total_interest == 0

    def test_total_principal_repaid(self):
        """총 상환 원금 = 대출 원금."""
        result = graduated_payment(300_000_000, 3.5, 360)
        total_principal = sum(p.principal_payment for p in result.monthly_payments)
        assert total_principal == 300_000_000


class TestRepaymentScheduleStructure:
    """RepaymentSchedule 구조 테스트."""

    def test_dataclass_immutable(self):
        """RepaymentSchedule, MonthlyPayment는 immutable."""
        result = equal_principal_and_interest(100_000_000, 3.0, 12)

        with pytest.raises(AttributeError):
            result.method = "modified"  # type: ignore[misc]

        with pytest.raises(AttributeError):
            result.monthly_payments[0].month = 999  # type: ignore[misc]

    def test_summary_consistency(self):
        """요약 필드가 monthly_payments와 일치."""
        result = equal_principal(200_000_000, 4.0, 240)

        calculated_interest = sum(p.interest_payment for p in result.monthly_payments)
        calculated_total = sum(p.total_payment for p in result.monthly_payments)
        max_payment = max(p.total_payment for p in result.monthly_payments)

        assert result.total_interest == calculated_interest
        assert result.total_payment == calculated_total
        assert result.max_month_payment == max_payment
        assert result.first_month_payment == result.monthly_payments[0].total_payment
        assert result.last_month_payment == result.monthly_payments[-1].total_payment
