"""조합 최적화 + API 통합 테스트."""

import pytest

from app.calculator.optimizer import simulate
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


class TestSimulateBasic:
    """기본 시뮬레이션 동작 확인."""

    def test_returns_combinations(self):
        """기본 조건으로 조합 반환."""
        req = _base_request()
        result = simulate(req)

        assert len(result.combinations) > 0
        assert result.disclaimer

    def test_combinations_ranked(self):
        """조합이 순위대로 정렬."""
        req = _base_request()
        result = simulate(req)

        for i, combo in enumerate(result.combinations):
            assert combo.rank == i + 1

    def test_total_interest_ascending(self):
        """총 이자 기준 오름차순."""
        req = _base_request()
        result = simulate(req)

        if len(result.combinations) > 1:
            for i in range(len(result.combinations) - 1):
                assert result.combinations[i].total_interest <= result.combinations[i + 1].total_interest


class TestScenarioNewlywed:
    """시나리오: 신혼 부부 4억 대출."""

    def test_newlywed_4억(self):
        req = _base_request(
            desired_amount=400_000_000,
            housing_price=500_000_000,
            annual_income=60_000_000,
            spouse_income=20_000_000,
            marital_status=MaritalStatus.NEWLYWED,
            is_first_time_buyer=True,
            is_homeless=True,
        )
        result = simulate(req)

        assert len(result.combinations) > 0

        # 디딤돌이 포함된 조합이 있어야 함
        has_didimdol = False
        for combo in result.combinations:
            for product in combo.products:
                if "디딤돌" in product.product_name:
                    has_didimdol = True
        assert has_didimdol

    def test_newlywed_discount(self):
        """신혼 우대금리 적용."""
        req = _base_request(
            marital_status=MaritalStatus.NEWLYWED,
            is_first_time_buyer=True,
        )
        result = simulate(req)

        for combo in result.combinations:
            for product in combo.products:
                if product.product_type == "policy":
                    assert product.discount_rate_pct > 0
                    assert len(product.discount_details) > 0


class TestScenarioSingle:
    """시나리오: 1인 가구 2억 대출."""

    def test_single_2억(self):
        req = _base_request(
            desired_amount=200_000_000,
            housing_price=300_000_000,
            annual_income=40_000_000,
            region=Region.METROPOLITAN,
        )
        result = simulate(req)
        assert len(result.combinations) > 0

    def test_single_high_income_no_policy(self):
        """고소득(1억) → 정책대출 부적격, 은행만."""
        req = _base_request(
            desired_amount=200_000_000,
            housing_price=800_000_000,
            annual_income=100_000_000,
        )
        result = simulate(req)

        for combo in result.combinations:
            for product in combo.products:
                assert product.product_type == "bank"

        assert any("정책대출" in w for w in result.warnings)


class TestScenarioRepaymentMethods:
    """상환 방식별 비교."""

    def test_equal_principal_less_interest(self):
        """원금균등이 원리금균등보다 총 이자가 적어야 함."""
        req_epi = _base_request(repayment_method=RepaymentMethod.EQUAL_PRINCIPAL_AND_INTEREST)
        req_ep = _base_request(repayment_method=RepaymentMethod.EQUAL_PRINCIPAL)

        result_epi = simulate(req_epi)
        result_ep = simulate(req_ep)

        if result_epi.combinations and result_ep.combinations:
            # 같은 유형의 첫 번째 조합끼리 비교
            assert result_ep.combinations[0].total_interest <= result_epi.combinations[0].total_interest


class TestDSRCheck:
    """DSR 비율이 합리적 범위인지."""

    def test_dsr_within_bounds(self):
        req = _base_request(annual_income=50_000_000)
        result = simulate(req)

        for combo in result.combinations:
            assert 0 <= combo.dsr_ratio <= 100

    def test_existing_debt_increases_dsr(self):
        """기존 부채가 DSR을 높여야 함."""
        req_no = _base_request(existing_debt_monthly=0)
        req_yes = _base_request(existing_debt_monthly=500_000)

        result_no = simulate(req_no)
        result_yes = simulate(req_yes)

        if result_no.combinations and result_yes.combinations:
            assert result_yes.combinations[0].dsr_ratio > result_no.combinations[0].dsr_ratio
