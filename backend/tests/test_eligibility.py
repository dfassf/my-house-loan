"""자격 판정 단위 테스트."""

import pytest

from app.rules.eligibility import check_eligibility
from app.rules.product_loader import load_bogeumjari, load_didimdol
from app.schemas.loan_input import (
    HousingType,
    LoanPurpose,
    LoanSimulationRequest,
    MaritalStatus,
    Region,
    RepaymentMethod,
)


def _base_request(**overrides) -> LoanSimulationRequest:
    """기본 테스트 요청 (디딤돌 자격 충족하는 기본값)."""
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


class TestDidimdolEligibility:
    """디딤돌 자격 판정."""

    def test_eligible_basic(self):
        """기본 조건 충족."""
        req = _base_request()
        result = check_eligibility(req, load_didimdol())
        assert result.eligible is True
        assert result.product_id == "didimdol"
        assert result.max_loan_amount > 0

    def test_not_homeless(self):
        """유주택자 → 부적격."""
        req = _base_request(is_homeless=False)
        result = check_eligibility(req, load_didimdol())
        assert result.eligible is False
        assert any("무주택" in r for r in result.reasons)

    def test_over_income(self):
        """소득 초과 → 부적격."""
        req = _base_request(annual_income=90_000_000)
        result = check_eligibility(req, load_didimdol())
        assert result.eligible is False
        assert any("소득 초과" in r for r in result.reasons)

    def test_newlywed_income_relaxed(self):
        """신혼 → 소득 상한 완화 (8500만원)."""
        req = _base_request(
            annual_income=80_000_000,
            marital_status=MaritalStatus.NEWLYWED,
        )
        result = check_eligibility(req, load_didimdol())
        assert result.eligible is True

    def test_newlywed_higher_price(self):
        """신혼 → 주택 가격 상한 완화 (6억)."""
        req = _base_request(
            housing_price=550_000_000,
            marital_status=MaritalStatus.NEWLYWED,
        )
        result = check_eligibility(req, load_didimdol())
        assert result.eligible is True

    def test_over_price(self):
        """주택 가격 초과."""
        req = _base_request(housing_price=600_000_000)
        result = check_eligibility(req, load_didimdol())
        assert result.eligible is False
        assert any("주택 가격 초과" in r for r in result.reasons)

    def test_over_area(self):
        """면적 초과."""
        req = _base_request(housing_area_m2=120.0)
        result = check_eligibility(req, load_didimdol())
        assert result.eligible is False

    def test_first_time_buyer_ltv_bonus(self):
        """생애최초 → LTV 80%."""
        req = _base_request(is_first_time_buyer=True)
        result = check_eligibility(req, load_didimdol())
        assert result.eligible is True
        assert result.max_ltv_pct == 80

    def test_first_time_buyer_higher_loan(self):
        """생애최초 → 대출 한도 2.4억."""
        req = _base_request(is_first_time_buyer=True)
        result = check_eligibility(req, load_didimdol())
        assert result.max_loan_amount == 240_000_000

    def test_newlywed_higher_loan(self):
        """신혼 → 대출 한도 3.2억."""
        req = _base_request(marital_status=MaritalStatus.NEWLYWED)
        result = check_eligibility(req, load_didimdol())
        assert result.max_loan_amount == 320_000_000

    def test_first_time_income_relaxed(self):
        """생애최초 → 소득 상한 완화 (7천만원)."""
        req = _base_request(
            annual_income=65_000_000,
            is_first_time_buyer=True,
        )
        result = check_eligibility(req, load_didimdol())
        assert result.eligible is True

    def test_married_no_income_boost(self):
        """기혼이라고 소득 상한이 올라가지 않음 (일반 6천만)."""
        req = _base_request(
            annual_income=65_000_000,
            marital_status=MaritalStatus.MARRIED,
        )
        result = check_eligibility(req, load_didimdol())
        assert result.eligible is False
        assert any("소득 초과" in r for r in result.reasons)

    def test_net_assets_exceeded(self):
        """순자산 초과 (5.11억 상한)."""
        req = _base_request(net_assets=520_000_000)
        result = check_eligibility(req, load_didimdol())
        assert result.eligible is False


class TestBogeumjariEligibility:
    """보금자리론 자격 판정."""

    def test_eligible_basic(self):
        req = _base_request()
        result = check_eligibility(req, load_bogeumjari())
        assert result.eligible is True
        assert result.product_id == "bogeumjari"

    def test_not_homeless_ok(self):
        """보금자리론은 유주택자도 가능."""
        req = _base_request(is_homeless=False)
        result = check_eligibility(req, load_bogeumjari())
        assert result.eligible is True

    def test_over_income(self):
        req = _base_request(annual_income=80_000_000)
        result = check_eligibility(req, load_bogeumjari())
        assert result.eligible is False

    def test_high_price(self):
        """6억 초과 → 부적격."""
        req = _base_request(housing_price=700_000_000)
        result = check_eligibility(req, load_bogeumjari())
        assert result.eligible is False
