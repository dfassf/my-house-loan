"""LTV/DSR 규제 테스트 — 10.15 부동산 대책 기준."""

import pytest

from app.rules.regulation import calculate_dsr, calculate_regulation_limits
from app.schemas.loan_input import (
    HousingType,
    LoanPurpose,
    LoanSimulationRequest,
    MaritalStatus,
    Region,
    RepaymentMethod,
)


def _base_request(**overrides) -> LoanSimulationRequest:
    defaults = dict(
        loan_purpose=LoanPurpose.PURCHASE,
        desired_amount=200_000_000,
        housing_price=400_000_000,
        housing_type=HousingType.APT,
        housing_area_m2=59.0,
        region=Region.SEOUL,
        annual_income=50_000_000,
        spouse_income=0,
        net_assets=200_000_000,
        marital_status=MaritalStatus.SINGLE,
        num_children=0,
        is_first_time_buyer=False,
        is_homeless=True,
        credit_score=800,
        existing_debt_monthly=0,
        repayment_method=RepaymentMethod.EQUAL_PRINCIPAL_AND_INTEREST,
        loan_term_years=30,
    )
    defaults.update(overrides)
    return LoanSimulationRequest(**defaults)


class TestRegulationLimits:
    """규제 한도 계산 — 10.15 대책 기준."""

    def test_seoul_homeless_general(self):
        """서울 무주택 일반 → LTV 40%."""
        req = _base_request(region=Region.SEOUL, housing_price=400_000_000)
        limits = calculate_regulation_limits(req)
        assert limits.ltv_limit_pct == 40
        assert limits.max_loan_by_ltv == 160_000_000

    def test_seoul_first_time(self):
        """서울 생애최초 → LTV 70%."""
        req = _base_request(region=Region.SEOUL, housing_price=400_000_000, is_first_time_buyer=True)
        limits = calculate_regulation_limits(req)
        assert limits.ltv_limit_pct == 70
        assert limits.max_loan_by_ltv == 280_000_000

    def test_seoul_homeowner(self):
        """서울 유주택자 → LTV 0%."""
        req = _base_request(region=Region.SEOUL, is_homeless=False)
        limits = calculate_regulation_limits(req)
        assert limits.ltv_limit_pct == 0
        assert limits.max_loan_by_ltv == 0

    def test_seoul_absolute_cap_15억이하(self):
        """서울 15억 이하 → 절대 한도 6억."""
        req = _base_request(
            region=Region.SEOUL,
            housing_price=1_200_000_000,
            is_first_time_buyer=True,  # LTV 70% → 8.4억이지만 cap 6억
            annual_income=100_000_000,
        )
        limits = calculate_regulation_limits(req)
        assert limits.max_loan_by_ltv == 600_000_000

    def test_seoul_absolute_cap_15억초과(self):
        """서울 15~25억 → 절대 한도 4억."""
        req = _base_request(
            region=Region.SEOUL,
            housing_price=2_000_000_000,
            is_first_time_buyer=True,  # LTV 70% → 14억이지만 cap 4억
            annual_income=200_000_000,
        )
        limits = calculate_regulation_limits(req)
        assert limits.max_loan_by_ltv == 400_000_000

    def test_non_metro_general(self):
        """비수도권 → LTV 70%."""
        req = _base_request(region=Region.NON_METROPOLITAN, housing_price=300_000_000)
        limits = calculate_regulation_limits(req)
        assert limits.ltv_limit_pct == 70

    def test_non_metro_first_time(self):
        """비수도권 생애최초 → LTV 80%."""
        req = _base_request(region=Region.NON_METROPOLITAN, is_first_time_buyer=True)
        limits = calculate_regulation_limits(req)
        assert limits.ltv_limit_pct == 80

    def test_dsr_limit_40(self):
        """DSR 한도 40%."""
        req = _base_request()
        limits = calculate_regulation_limits(req)
        assert limits.dsr_limit_pct == 40

    def test_stress_dsr_reduces_max(self):
        """스트레스 DSR(+3%) 적용으로 최대 대출 감소."""
        req_regulated = _base_request(region=Region.SEOUL, annual_income=60_000_000)
        req_non_regulated = _base_request(region=Region.NON_METROPOLITAN, annual_income=60_000_000)

        limits_reg = calculate_regulation_limits(req_regulated)
        limits_non = calculate_regulation_limits(req_non_regulated)

        # 규제지역(+3%)이 비규제(+1.5%)보다 DSR 한도가 더 작아야 함
        assert limits_reg.max_loan_by_dsr < limits_non.max_loan_by_dsr

    def test_existing_debt_reduces_max(self):
        """기존 부채가 있으면 최대 대출금액 감소."""
        req_no_debt = _base_request(annual_income=60_000_000)
        req_with_debt = _base_request(annual_income=60_000_000, existing_debt_monthly=1_000_000)

        limits_no = calculate_regulation_limits(req_no_debt)
        limits_with = calculate_regulation_limits(req_with_debt)

        assert limits_with.max_loan_by_dsr < limits_no.max_loan_by_dsr

    def test_policy_dsr_exempt(self):
        """정책대출 DSR 면제 시 max_loan_by_dsr가 LTV 기준으로."""
        req = _base_request()
        limits = calculate_regulation_limits(req, policy_exempt_dsr=True)
        assert limits.max_loan_by_dsr == limits.max_loan_by_ltv


class TestDSRCalculation:
    """DSR 비율 계산."""

    def test_basic(self):
        assert calculate_dsr(60_000_000, 24_000_000) == 40.0

    def test_zero_income(self):
        assert calculate_dsr(0, 100_000) == 100.0

    def test_zero_repayment(self):
        assert calculate_dsr(50_000_000, 0) == 0.0
