/**
 * 대출 시뮬레이터 프론트엔드 타입 정의.
 * 백엔드 Pydantic 스키마와 1:1 대응.
 */

// ─── 입력 Enum 타입 ───

export type MaritalStatus = 'single' | 'married' | 'newlywed'
export type RepaymentMethod = 'equal_principal_and_interest' | 'equal_principal' | 'graduated'
export type HousingType = 'apt' | 'non_apt'
export type Region = 'seoul' | 'metropolitan' | 'non_metropolitan'
export type LoanPurpose = 'purchase' | 'jeonse'

// ─── 입력 폼 ───

export interface LoanSimulationInput {
  loan_purpose: LoanPurpose
  desired_amount: number
  housing_price: number
  housing_type: HousingType
  housing_area_m2: number
  region: Region

  annual_income: number
  spouse_income: number
  net_assets: number

  marital_status: MaritalStatus
  num_children: number
  is_first_time_buyer: boolean
  is_homeless: boolean

  credit_score: number
  existing_debt_monthly: number

  repayment_method: RepaymentMethod
  loan_term_years: number
}

// ─── 결과 타입 ───

export interface LoanProductResult {
  product_name: string
  product_type: 'policy' | 'bank'
  loan_amount: number
  annual_rate_pct: number
  base_rate_pct: number
  discount_rate_pct: number
  discount_details: string[]
  monthly_payment: number
  total_interest: number
  total_payment: number
  loan_term_years: number
  repayment_method: string
  eligibility_notes: string[]
}

export interface CombinationResult {
  rank: number
  products: LoanProductResult[]
  total_loan_amount: number
  total_monthly_payment: number
  total_interest: number
  total_payment: number
  weighted_avg_rate: number
  dsr_ratio: number
  ltv_ratio: number
  label: string
}

export interface PolicyRejection {
  product_name: string
  reasons: string[]
}

export interface SimulationResponse {
  combinations: CombinationResult[]
  max_loanable: number
  ltv_limit_pct: number
  dsr_limit_pct: number
  warnings: string[]
  policy_rejections: PolicyRejection[]
  disclaimer: string
}

// ─── UI 상태 ───

export type InputStep = 1 | 2 | 3
export type AppStep = 'input' | 'loading' | 'result'

// ─── 라벨 매핑 ───

export const MARITAL_LABELS: Record<MaritalStatus, string> = {
  single: '미혼',
  married: '기혼',
  newlywed: '신혼(7년 이내)',
}

export const REPAYMENT_LABELS: Record<RepaymentMethod, string> = {
  equal_principal_and_interest: '원리금균등',
  equal_principal: '원금균등',
  graduated: '채증식',
}

export const HOUSING_TYPE_LABELS: Record<HousingType, string> = {
  apt: '아파트',
  non_apt: '빌라·다세대 등',
}

export const REGION_LABELS: Record<Region, string> = {
  seoul: '서울',
  metropolitan: '수도권(인천·경기)',
  non_metropolitan: '비수도권',
}

export const LOAN_PURPOSE_LABELS: Record<LoanPurpose, string> = {
  purchase: '주택 구입',
  jeonse: '전세',
}
