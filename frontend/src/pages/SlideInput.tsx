import { useState, useCallback, useRef, useEffect } from 'react'
import type { LoanSimulationInput, MaritalStatus, HousingType, Region, RepaymentMethod } from '../types'

const TOTAL_SLIDES = 8

interface Props {
  onSubmit: (input: LoanSimulationInput) => void
  loading: boolean
}

// ─── Slide data types ───
type HouseholdType = 'general' | 'newlywed' | 'multi_child'
type HouseStatus = 'first_time' | 'homeless' | 'one_dispose' | 'owner'
type ChildrenCount = 'none' | '1' | '2+'

interface SlideState {
  household: HouseholdType | null
  houseStatus: HouseStatus | null
  children: ChildrenCount | null
  annualIncome: string         // 만원
  housingPrice: string         // 억원
  netAssets: string            // 억원
  region: Region | null
  repaymentMethod: RepaymentMethod | null
}

function deriveInput(s: SlideState): LoanSimulationInput {
  const incomeMan = parseFloat(s.annualIncome) || 0
  const priceEok = parseFloat(s.housingPrice) || 0
  const assetEok = parseFloat(s.netAssets) || 0

  let maritalStatus: MaritalStatus = 'single'
  if (s.household === 'newlywed') maritalStatus = 'newlywed'
  else if (s.household === 'multi_child' || s.household === 'general') maritalStatus = 'married'

  const numChildren = s.children === '2+' ? 2 : s.children === '1' ? 1 : 0

  return {
    loan_purpose: 'purchase',
    desired_amount: Math.round(priceEok * 0.7 * 100_000_000),
    housing_price: Math.round(priceEok * 100_000_000),
    housing_type: 'apt' as HousingType,
    housing_area_m2: 59,
    region: s.region || 'seoul',
    annual_income: incomeMan * 10_000,
    spouse_income: 0,
    net_assets: Math.round(assetEok * 100_000_000),
    marital_status: maritalStatus,
    num_children: numChildren,
    is_first_time_buyer: s.houseStatus === 'first_time',
    is_homeless: s.houseStatus === 'first_time' || s.houseStatus === 'homeless',
    credit_score: 800,
    existing_debt_monthly: 0,
    repayment_method: s.repaymentMethod || 'equal_principal_and_interest',
    loan_term_years: 30,
  }
}

export default function SlideInput({ onSubmit, loading }: Props) {
  const [current, setCurrent] = useState(0)
  const [state, setState] = useState<SlideState>({
    household: null,
    houseStatus: null,
    children: null,
    annualIncome: '',
    housingPrice: '',
    netAssets: '',
    region: null,
    repaymentMethod: null,
  })
  const [exitSlide, setExitSlide] = useState<number | null>(null)
  const slidesRef = useRef<HTMLDivElement>(null)

  const update = useCallback(<K extends keyof SlideState>(key: K, val: SlideState[K]) => {
    setState(prev => ({ ...prev, [key]: val }))
  }, [])

  function canProceed(): boolean {
    switch (current) {
      case 0: return !!state.household
      case 1: return !!state.houseStatus
      case 2: return !!state.children
      case 3: return state.annualIncome !== '' && parseFloat(state.annualIncome) > 0
      case 4: return state.housingPrice !== '' && parseFloat(state.housingPrice) > 0
      case 5: return state.netAssets !== ''
      case 6: return !!state.region
      case 7: return !!state.repaymentMethod
      default: return true
    }
  }

  function navigateTo(next: number) {
    setExitSlide(current)
    setCurrent(next)
    setTimeout(() => setExitSlide(null), 380)
  }

  function goNext() {
    if (current === TOTAL_SLIDES - 1) {
      onSubmit(deriveInput(state))
      return
    }
    navigateTo(current + 1)
  }

  function goBack() {
    if (current > 0) navigateTo(current - 1)
  }

  // Auto-focus number inputs
  useEffect(() => {
    if (current >= 3 && current <= 5) {
      const timer = setTimeout(() => {
        const input = slidesRef.current?.querySelector(`.slide[data-slide="${current}"] input`) as HTMLInputElement | null
        input?.focus()
      }, 400)
      return () => clearTimeout(timer)
    }
  }, [current])

  const progressPct = Math.round((current / TOTAL_SLIDES) * 100)

  return (
    <div className="app">
      {/* Progress */}
      <div className="progress-wrap">
        <div className="progress-track">
          <div className="progress-fill" style={{ width: `${progressPct}%` }} />
        </div>
        <div className="progress-label">{current + 1} / {TOTAL_SLIDES}</div>
      </div>

      {/* Slides */}
      <div className="slides" ref={slidesRef}>
        {/* 0: 가구유형 */}
        <Slide index={0} current={current} exitSlide={exitSlide}>
          <div>
            <div className="slide-question">가구유형이<br />어떻게 되시나요?</div>
          </div>
          <div className="options">
            <OptionCard
              title="일반"
              selected={state.household === 'general'}
              onClick={() => update('household', 'general')}
            />
            <OptionCard
              title="신혼부부"
              desc="혼인 신고 후 7년 이내"
              selected={state.household === 'newlywed'}
              onClick={() => update('household', 'newlywed')}
            />
            <OptionCard
              title="2자녀 이상 가구"
              selected={state.household === 'multi_child'}
              onClick={() => update('household', 'multi_child')}
            />
          </div>
        </Slide>

        {/* 1: 주택 매매 경험 */}
        <Slide index={1} current={current} exitSlide={exitSlide}>
          <div>
            <div className="slide-question">주택 매매 경험이<br />있으신가요?</div>
            <div className="slide-sub">구매 이력과 현재 보유 여부를 기준으로 선택해주세요</div>
          </div>
          <div className="options">
            <OptionCard
              title="한 번도 없어요"
              desc="생애 최초 구매 — 매매 경험이 전혀 없음"
              selected={state.houseStatus === 'first_time'}
              onClick={() => update('houseStatus', 'first_time')}
            />
            <OptionCard
              title="있지만 지금은 없어요"
              desc="무주택 — 매매 경험은 있으나 현재 미보유"
              selected={state.houseStatus === 'homeless'}
              onClick={() => update('houseStatus', 'homeless')}
            />
            <OptionCard
              title="1채 보유 · 팔고 살 예정"
              desc="1주택 처분 조건 — 기존 주택 매도 후 구입"
              selected={state.houseStatus === 'one_dispose'}
              onClick={() => update('houseStatus', 'one_dispose')}
            />
            <OptionCard
              title="1채 이상 보유 중"
              desc="1주택 이상 — 처분 계획 없이 추가 구입"
              selected={state.houseStatus === 'owner'}
              onClick={() => update('houseStatus', 'owner')}
            />
          </div>
        </Slide>

        {/* 2: 자녀 수 */}
        <Slide index={2} current={current} exitSlide={exitSlide}>
          <div>
            <div className="slide-question">자녀가 몇 명<br />있으신가요?</div>
          </div>
          <div className="options">
            <OptionCard title="없음" selected={state.children === 'none'} onClick={() => update('children', 'none')} />
            <OptionCard title="1명" selected={state.children === '1'} onClick={() => update('children', '1')} />
            <OptionCard title="2명 이상" selected={state.children === '2+'} onClick={() => update('children', '2+')} />
          </div>
        </Slide>

        {/* 3: 연소득 */}
        <Slide index={3} current={current} exitSlide={exitSlide}>
          <div>
            <div className="slide-question">가구 합산<br />연소득은요?</div>
            <div className="slide-sub">부부 합산 세전 연간 소득을 입력해주세요</div>
          </div>
          <div className="number-input-wrap">
            <div className="number-field">
              <input
                type="number"
                placeholder="0"
                min={0}
                inputMode="numeric"
                value={state.annualIncome}
                onChange={e => update('annualIncome', e.target.value)}
                onKeyDown={e => e.key === 'Enter' && canProceed() && goNext()}
              />
              <span className="number-unit">만원 / 년</span>
            </div>
          </div>
        </Slide>

        {/* 4: 주택 가격 */}
        <Slide index={4} current={current} exitSlide={exitSlide}>
          <div>
            <div className="slide-question">구입하려는<br />주택 가격은요?</div>
            <div className="slide-sub">실거래가 기준으로 입력해주세요</div>
          </div>
          <div className="number-input-wrap">
            <div className="number-field">
              <input
                type="number"
                placeholder="0.0"
                step={0.1}
                min={0}
                inputMode="decimal"
                value={state.housingPrice}
                onChange={e => update('housingPrice', e.target.value)}
                onKeyDown={e => e.key === 'Enter' && canProceed() && goNext()}
              />
              <span className="number-unit">억원</span>
            </div>
          </div>
        </Slide>

        {/* 5: 순자산 */}
        <Slide index={5} current={current} exitSlide={exitSlide}>
          <div>
            <div className="slide-question">보유 순자산<br />규모는요?</div>
            <div className="slide-sub">총 자산에서 부채를 제외한 금액이에요</div>
          </div>
          <div className="number-input-wrap">
            <div className="number-field">
              <input
                type="number"
                placeholder="0.0"
                step={0.1}
                min={0}
                inputMode="decimal"
                value={state.netAssets}
                onChange={e => update('netAssets', e.target.value)}
                onKeyDown={e => e.key === 'Enter' && canProceed() && goNext()}
              />
              <span className="number-unit">억원</span>
            </div>
          </div>
        </Slide>

        {/* 6: 지역 */}
        <Slide index={6} current={current} exitSlide={exitSlide}>
          <div>
            <div className="slide-question">주택이 어디에<br />위치하나요?</div>
            <div className="slide-sub">규제지역 여부에 따라 LTV/DSR이 달라져요</div>
          </div>
          <div className="options">
            <OptionCard
              title="서울"
              desc="규제지역 — LTV 40% (생애최초 70%)"
              selected={state.region === 'seoul'}
              onClick={() => update('region', 'seoul')}
            />
            <OptionCard
              title="수도권 (인천, 경기)"
              desc="일부 규제지역 포함"
              selected={state.region === 'metropolitan'}
              onClick={() => update('region', 'metropolitan')}
            />
            <OptionCard
              title="비수도권"
              desc="비규제 — LTV 70% (생애최초 80%)"
              selected={state.region === 'non_metropolitan'}
              onClick={() => update('region', 'non_metropolitan')}
            />
          </div>
        </Slide>

        {/* 7: 상환방식 */}
        <Slide index={7} current={current} exitSlide={exitSlide}>
          <div>
            <div className="slide-question">선호하는<br />상환방식은요?</div>
          </div>
          <div className="options">
            <OptionCard
              title="원리금균등"
              desc="매월 납부액(원금+이자)이 일정"
              selected={state.repaymentMethod === 'equal_principal_and_interest'}
              onClick={() => update('repaymentMethod', 'equal_principal_and_interest')}
            />
            <OptionCard
              title="원금균등"
              desc="매월 같은 원금, 이자는 점점 감소"
              selected={state.repaymentMethod === 'equal_principal'}
              onClick={() => update('repaymentMethod', 'equal_principal')}
            />
            <OptionCard
              title="체증식"
              desc="초반 적게, 시간이 갈수록 상환액 증가"
              selected={state.repaymentMethod === 'graduated'}
              onClick={() => update('repaymentMethod', 'graduated')}
            />
          </div>
        </Slide>
      </div>

      {/* Bottom Nav */}
      <div className="bottom-nav">
        <button className="btn-back" onClick={goBack} disabled={current === 0}>
          ←
        </button>
        <button className="btn-next" onClick={goNext} disabled={!canProceed() || loading}>
          {current === TOTAL_SLIDES - 1 ? (loading ? '계산 중...' : '결과 보기') : '다음'}
        </button>
      </div>
    </div>
  )
}

// ─── Sub-components ───

function Slide({ index, current, exitSlide, children }: {
  index: number
  current: number
  exitSlide: number | null
  children: React.ReactNode
}) {
  let cls = 'slide'
  if (index === current) cls += ' active'
  if (index === exitSlide) cls += ' exit'

  return (
    <div className={cls} data-slide={index}>
      {children}
    </div>
  )
}

function OptionCard({ title, desc, selected, onClick }: {
  title: string
  desc?: string
  selected: boolean
  onClick: () => void
}) {
  return (
    <div className={`option-card${selected ? ' selected' : ''}`} onClick={onClick}>
      <div>
        <div className="option-title">{title}</div>
        {desc && <div className="option-desc">{desc}</div>}
      </div>
      <div className="option-check" />
    </div>
  )
}
