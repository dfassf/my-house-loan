"""정책대출 상품 룰 정의 스키마."""

from pydantic import BaseModel, Field


class RateRange(BaseModel):
    """금리 범위."""

    min_rate: float = Field(ge=0, description="최저 금리 (%)")
    max_rate: float = Field(ge=0, description="최고 금리 (%)")


class IncomeRateTier(BaseModel):
    """소득 구간별 금리."""

    max_income: int = Field(description="소득 상한 (원, 이하)")
    rate_pct: float = Field(ge=0, description="적용 금리 (%)")


class DiscountCondition(BaseModel):
    """우대 금리 조건."""

    name: str = Field(description="우대 항목명")
    discount_pct: float = Field(ge=0, description="할인 금리 (%p)")
    condition_description: str = Field(description="적용 조건 설명")


class PolicyLoanProduct(BaseModel):
    """정책대출 상품 정의 (디딤돌, 보금자리론 등)."""

    product_id: str = Field(description="상품 ID")
    product_name: str = Field(description="상품명")
    product_type: str = Field(default="policy", description="상품 유형")

    # 자격 조건
    max_housing_price: int = Field(description="주택 가격 상한 (원)")
    max_income: int = Field(description="소득 상한 (원)")
    max_net_assets: int = Field(description="순자산 상한 (원)")
    requires_homeless: bool = Field(default=True, description="무주택 요건")
    min_area_m2: float = Field(ge=0, default=0, description="최소 전용면적 (m²)")
    max_area_m2: float = Field(ge=0, default=85, description="최대 전용면적 (m²)")

    # 대출 한도
    max_loan_amount: int = Field(description="최대 대출금액 (원)")
    max_ltv_pct: float = Field(ge=0, le=100, description="최대 LTV (%)")

    # 금리
    income_rate_tiers: list[IncomeRateTier] = Field(description="소득 구간별 기본 금리")
    discount_conditions: list[DiscountCondition] = Field(
        default_factory=list,
        description="우대 금리 조건 목록",
    )
    max_total_discount: float = Field(ge=0, default=0.7, description="최대 우대 합계 (%p)")

    # 상환 조건
    available_terms_years: list[int] = Field(description="선택 가능 대출 기간 (년)")
    available_repayment_methods: list[str] = Field(description="선택 가능 상환 방식")
