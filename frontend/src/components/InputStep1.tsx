import type { LoanSimulationInput, LoanPurpose, HousingType, Region } from '../types'
import { LOAN_PURPOSE_LABELS, HOUSING_TYPE_LABELS, REGION_LABELS } from '../types'
import AmountInput from './AmountInput'
import type { AmountChip } from './AmountInput'

interface Props {
  data: LoanSimulationInput
  onChange: (patch: Partial<LoanSimulationInput>) => void
  onNext: () => void
}

const AMOUNT_CHIPS: AmountChip[] = [
  { label: '+1억', amount: 100_000_000 },
  { label: '+1,000만', amount: 10_000_000 },
  { label: '+100만', amount: 1_000_000 },
]

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
