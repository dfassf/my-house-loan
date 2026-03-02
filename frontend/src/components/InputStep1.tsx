import type { LoanSimulationInput, LoanPurpose, HousingType, Region } from '../types'
import { LOAN_PURPOSE_LABELS, HOUSING_TYPE_LABELS, REGION_LABELS } from '../types'

interface Props {
  data: LoanSimulationInput
  onChange: (patch: Partial<LoanSimulationInput>) => void
  onNext: () => void
}

function formatWon(value: number): string {
  if (value >= 100_000_000) {
    const uk = Math.floor(value / 100_000_000)
    const man = Math.floor((value % 100_000_000) / 10_000)
    return man > 0 ? `${uk}억 ${man.toLocaleString()}만원` : `${uk}억원`
  }
  if (value >= 10_000) {
    return `${(value / 10_000).toLocaleString()}만원`
  }
  return `${value.toLocaleString()}원`
}

/** 만원 단위 입력 → 원 단위 변환 */
function manToWon(manStr: string): number {
  const n = parseFloat(manStr)
  return isNaN(n) ? 0 : Math.round(n * 10_000)
}

/** 원 단위 → 만원 단위 (표시용) */
function wonToMan(won: number): string {
  const man = won / 10_000
  return man === 0 ? '' : String(man)
}

interface AmountChip {
  label: string
  amount: number
}

const AMOUNT_CHIPS: AmountChip[] = [
  { label: '+1억', amount: 100_000_000 },
  { label: '+1,000만', amount: 10_000_000 },
  { label: '+100만', amount: 1_000_000 },
]

function AmountInput({
  value,
  onChange,
  chips,
  placeholder = '0',
  warn,
}: {
  value: number
  onChange: (v: number) => void
  chips: AmountChip[]
  placeholder?: string
  warn?: string
}) {
  return (
    <div className="amount-input-group">
      <div className="amount-input-row">
        <input
          type="number"
          className="amount-input"
          placeholder={placeholder}
          value={wonToMan(value)}
          onChange={e => onChange(manToWon(e.target.value))}
        />
        <span className="amount-input-suffix">만원</span>
      </div>
      <div className="amount-display">{formatWon(value)}</div>
      {warn && <div className="field-warn">{warn}</div>}
      <div className="amount-chips">
        {chips.map(chip => (
          <button
            key={chip.label}
            className="amount-chip"
            onClick={() => onChange(Math.max(0, value + chip.amount))}
          >
            {chip.label}
          </button>
        ))}
        <button
          className="amount-chip amount-chip-reset"
          onClick={() => onChange(0)}
        >
          초기화
        </button>
      </div>
    </div>
  )
}

export default function InputStep1({ data, onChange, onNext }: Props) {
  const loanExceedsPrice = data.desired_amount > data.housing_price && data.housing_price > 0
  const canProceed =
    data.desired_amount >= 10_000_000 &&
    data.housing_price >= 10_000_000 &&
    data.housing_area_m2 >= 10 &&
    !loanExceedsPrice

  return (
    <div className="input-step">
      <h2 className="step-title">어떤 대출이 필요해요?</h2>

      <label className="field-label">대출 목적</label>
      <div className="radio-group">
        {(Object.entries(LOAN_PURPOSE_LABELS) as [LoanPurpose, string][]).map(([val, label]) => (
          <button
            key={val}
            className={`radio-btn ${data.loan_purpose === val ? 'active' : ''}`}
            onClick={() => onChange({ loan_purpose: val })}
          >
            {label}
          </button>
        ))}
      </div>

      <label className="field-label">받고 싶은 금액</label>
      <AmountInput
        value={data.desired_amount}
        onChange={v => onChange({ desired_amount: v })}
        chips={AMOUNT_CHIPS}
        warn={loanExceedsPrice ? '대출금액이 주택 가격보다 많아요' : undefined}
      />

      <label className="field-label">주택 가격</label>
      <AmountInput
        value={data.housing_price}
        onChange={v => onChange({ housing_price: v })}
        chips={AMOUNT_CHIPS}
      />

      <label className="field-label">주택 유형</label>
      <div className="radio-group">
        {(Object.entries(HOUSING_TYPE_LABELS) as [HousingType, string][]).map(([val, label]) => (
          <button
            key={val}
            className={`radio-btn ${data.housing_type === val ? 'active' : ''}`}
            onClick={() => onChange({ housing_type: val })}
          >
            {label}
          </button>
        ))}
      </div>

      <label className="field-label">전용면적(m²)</label>
      <input
        type="number"
        min={10}
        max={300}
        step={0.1}
        value={data.housing_area_m2}
        onChange={e => onChange({ housing_area_m2: Number(e.target.value) })}
        className="number-input"
      />

      <label className="field-label">지역</label>
      <div className="radio-group">
        {(Object.entries(REGION_LABELS) as [Region, string][]).map(([val, label]) => (
          <button
            key={val}
            className={`radio-btn ${data.region === val ? 'active' : ''}`}
            onClick={() => onChange({ region: val })}
          >
            {label}
          </button>
        ))}
      </div>

      <button className="btn btn-primary btn-full" onClick={onNext} disabled={!canProceed}>
        다음
      </button>
    </div>
  )
}
