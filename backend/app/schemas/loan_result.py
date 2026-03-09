"""대출 시뮬레이션 결과 스키마."""

from pydantic import BaseModel, Field


class LoanProductResult(BaseModel):
    """개별 대출 상품 계산 결과."""

    product_id: str = Field(default="", description="상품 식별자 (예: didimdol, bogeumjari, bank)")
    product_name: str = Field(description="상품명 (예: 디딤돌, 보금자리론)")
    product_type: str = Field(description="상품 유형 (policy / bank)")
    loan_amount: int = Field(ge=0, description="대출금액 (원)")
    annual_rate_pct: float = Field(ge=0, description="적용 금리 (%)")
    base_rate_pct: float = Field(ge=0, description="기본 금리 (%)")
    discount_rate_pct: float = Field(ge=0, default=0, description="우대 금리 합계 (%)")
    discount_details: list[str] = Field(default_factory=list, description="우대 금리 내역")
    monthly_payment: int = Field(ge=0, description="월 납입금 (원)")
    total_interest: int = Field(ge=0, description="총 이자 (원)")
    total_payment: int = Field(ge=0, description="총 납입금 (원)")
    loan_term_years: int = Field(ge=1, description="대출 기간 (년)")
    repayment_method: str = Field(description="상환 방식")
    eligibility_notes: list[str] = Field(default_factory=list, description="자격 조건 참고")


class CombinationResult(BaseModel):
    """대출 조합 (정책대출 + 은행대출)."""

    rank: int = Field(ge=1, description="순위")
    products: list[LoanProductResult] = Field(description="포함된 대출 상품들")
    total_loan_amount: int = Field(ge=0, description="총 대출금액")
    total_monthly_payment: int = Field(ge=0, description="총 월 납입금")
    total_interest: int = Field(ge=0, description="총 이자")
    total_payment: int = Field(ge=0, description="총 납입금")
    weighted_avg_rate: float = Field(ge=0, description="가중평균 금리 (%)")
    dsr_ratio: float = Field(ge=0, description="DSR 비율 (%)")
    ltv_ratio: float = Field(ge=0, description="LTV 비율 (%)")
    label: str = Field(default="", description="조합 요약 라벨")


class PolicyRejection(BaseModel):
    """정책대출 탈락 사유."""

    product_name: str = Field(description="상품명")
    reasons: list[str] = Field(description="탈락 사유 목록")


class SimulationResponse(BaseModel):
    """시뮬레이션 전체 응답."""

    combinations: list[CombinationResult] = Field(description="추천 조합 목록 (최적순)")
    max_loanable: int = Field(ge=0, description="규제 내 최대 대출 가능금액")
    ltv_limit_pct: float = Field(ge=0, description="적용된 LTV 한도 (%)")
    dsr_limit_pct: float = Field(ge=0, description="적용된 DSR 한도 (%)")
    warnings: list[str] = Field(default_factory=list, description="경고 메시지")
    policy_rejections: list[PolicyRejection] = Field(default_factory=list, description="정책대출 탈락 사유")
    disclaimer: str = Field(
        default="이 결과는 참고용이에요. 실제 대출 조건은 금융기관 심사에 따라 달라질 수 있어요.",
        description="면책 조항",
    )
