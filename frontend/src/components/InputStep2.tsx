import type { LoanSimulationInput, MaritalStatus } from '../types'
import { MARITAL_LABELS } from '../types'

interface Props {
  data: LoanSimulationInput
  onChange: (patch: Partial<LoanSimulationInput>) => void
  onNext: () => void
  onBack: () => void
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
  return value === 0 ? '0원' : `${value.toLocaleString()}원`
}

function manToWon(manStr: string): number {
  const n = parseFloat(manStr)
  return isNaN(n) ? 0 : Math.round(n * 10_000)
}

function wonToMan(won: number): string {
  const man = won / 10_000
  return man === 0 ? '' : String(man)
}

interface AmountChip {
  label: string
  amount: number // 원 단위
}

const INCOME_CHIPS: AmountChip[] = [
  { label: '+1,000만', amount: 10_000_000 },
  { label: '+500만', amount: 5_000_000 },
  { label: '+100만', amount: 1_000_000 },
]

const ASSET_CHIPS: AmountChip[] = [
  { label: '+1억', amount: 100_000_000 },
  { label: '+1,000만', amount: 10_000_000 },
  { label: '+100만', amount: 1_000_000 },
]

function AmountInput({
  value,
  onChange,
  chips,
  placeholder = '0',
}: {
  value: number
  onChange: (v: number) => void
  chips: AmountChip[]
  placeholder?: string
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

export default function InputStep2({ data, onChange, onNext, onBack }: Props) {
  return (
    <div className="input-step">
      <h2 className="step-title">가구 정보를 알려주세요</h2>

      <label className="field-label">혼인 상태</label>
      <div className="radio-group">
        {(Object.entries(MARITAL_LABELS) as [MaritalStatus, string][]).map(([val, label]) => (
          <button
            key={val}
            className={`radio-btn ${data.marital_status === val ? 'active' : ''}`}
            onClick={() => {
              const patch: Partial<LoanSimulationInput> = { marital_status: val }
              if (val === 'single') patch.spouse_income = 0
              onChange(patch)
            }}
          >
            {label}
          </button>
        ))}
      </div>

      <label className="field-label">자녀 수</label>
      <div className="counter-group">
        <button
          className="counter-btn"
          onClick={() => onChange({ num_children: Math.max(0, data.num_children - 1) })}
          disabled={data.num_children <= 0}
        >
          -
        </button>
        <span className="counter-value">{data.num_children}명</span>
        <button
          className="counter-btn"
          onClick={() => onChange({ num_children: Math.min(10, data.num_children + 1) })}
        >
          +
        </button>
      </div>

      <label className="field-label">연소득</label>
      <AmountInput
        value={data.annual_income}
        onChange={v => onChange({ annual_income: v })}
        chips={INCOME_CHIPS}
      />

      {data.marital_status !== 'single' && (
        <>
          <label className="field-label">배우자 연소득</label>
          <AmountInput
            value={data.spouse_income}
            onChange={v => onChange({ spouse_income: v })}
            chips={INCOME_CHIPS}
          />
        </>
      )}

      <label className="field-label">순자산</label>
      <AmountInput
        value={data.net_assets}
        onChange={v => onChange({ net_assets: v })}
        chips={ASSET_CHIPS}
      />

      <div className="checkbox-group">
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={data.is_first_time_buyer}
            onChange={e => {
              const checked = e.target.checked
              const patch: Partial<LoanSimulationInput> = { is_first_time_buyer: checked }
              if (checked) patch.is_homeless = true
              onChange(patch)
            }}
          />
          생애최초로 집을 사요
        </label>

        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={data.is_homeless}
            onChange={e => {
              const checked = e.target.checked
              const patch: Partial<LoanSimulationInput> = { is_homeless: checked }
              if (!checked) patch.is_first_time_buyer = false
              onChange(patch)
            }}
          />
          지금 집이 없어요
        </label>
      </div>

      <div className="step-buttons">
        <button className="btn btn-ghost" onClick={onBack}>이전</button>
        <button className="btn btn-primary" onClick={onNext}>다음</button>
      </div>
    </div>
  )
}
