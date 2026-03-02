"""대출 시뮬레이션 입력 스키마."""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class MaritalStatus(str, Enum):
    SINGLE = "single"
    MARRIED = "married"
    NEWLYWED = "newlywed"  # 신혼 (혼인 7년 이내)


class RepaymentMethod(str, Enum):
    EQUAL_PRINCIPAL_AND_INTEREST = "equal_principal_and_interest"  # 원리금균등
    EQUAL_PRINCIPAL = "equal_principal"  # 원금균등
    GRADUATED = "graduated"  # 채증식


class HousingType(str, Enum):
    APT = "apt"  # 아파트
    NON_APT = "non_apt"  # 비아파트 (빌라, 다세대 등)


class Region(str, Enum):
    SEOUL = "seoul"
    METROPOLITAN = "metropolitan"  # 수도권 (인천, 경기)
    NON_METROPOLITAN = "non_metropolitan"  # 비수도권


class LoanPurpose(str, Enum):
    PURCHASE = "purchase"  # 주택 구입
    JEONSE = "jeonse"  # 전세


class LoanSimulationRequest(BaseModel):
    """대출 시뮬레이션 요청."""

    # 기본 정보
    loan_purpose: LoanPurpose = Field(description="대출 목적 (구입/전세)")
    desired_amount: int = Field(ge=10_000_000, le=1_000_000_000, description="희망 대출금액 (원)")
    housing_price: int = Field(ge=10_000_000, le=5_000_000_000, description="주택 가격 (원)")
    housing_type: HousingType = Field(description="주택 유형")
    housing_area_m2: float = Field(ge=10.0, le=300.0, description="전용면적 (m²)")
    region: Region = Field(description="지역")

    # 소득/자산
    annual_income: int = Field(ge=0, le=1_000_000_000, description="연소득 (원)")
    spouse_income: int = Field(ge=0, le=1_000_000_000, default=0, description="배우자 연소득 (원)")
    net_assets: int = Field(ge=0, le=10_000_000_000, default=0, description="순자산 (원)")

    # 가구 정보
    marital_status: MaritalStatus = Field(description="혼인 상태")
    num_children: int = Field(ge=0, le=10, default=0, description="자녀 수")
    is_first_time_buyer: bool = Field(default=False, description="생애최초 주택구입 여부")
    is_homeless: bool = Field(default=True, description="무주택 여부")

    # 신용/부채
    credit_score: int = Field(ge=0, le=1000, default=800, description="신용점수 (NICE 기준)")
    existing_debt_monthly: int = Field(ge=0, default=0, description="기존 월상환액 (원)")

    # 상환 조건
    repayment_method: RepaymentMethod = Field(
        default=RepaymentMethod.EQUAL_PRINCIPAL_AND_INTEREST,
        description="상환 방식",
    )
    loan_term_years: int = Field(ge=1, le=50, default=30, description="대출 기간 (년)")

    @model_validator(mode="after")
    def _cross_field_validation(self) -> "LoanSimulationRequest":
        if self.desired_amount > self.housing_price:
            msg = "대출금액이 주택 가격보다 많아요"
            raise ValueError(msg)
        if self.is_first_time_buyer and not self.is_homeless:
            msg = "생애최초 구입자는 무주택이어야 해요"
            raise ValueError(msg)
        return self

    @property
    def loan_term_months(self) -> int:
        return self.loan_term_years * 12

    @property
    def total_household_income(self) -> int:
        return self.annual_income + self.spouse_income
