import type { LoanSimulationInput, RepaymentMethod } from '../types'
import { REPAYMENT_LABELS } from '../types'

interface Props {
  data: LoanSimulationInput
  onChange: (patch: Partial<LoanSimulationInput>) => void
  onSubmit: () => void
  onBack: () => void
  loading: boolean
}

function formatWon(value: number): string {
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

const CREDIT_PRESETS = [700, 800, 900]

const DEBT_CHIPS = [
  { label: '+50만', amount: 500_000 },
  { label: '+10만', amount: 100_000 },
  { label: '+5만', amount: 50_000 },
]

export default function InputStep3({ data, onChange, onSubmit, onBack, loading }: Props) {
  return (
    <div className="input-step">
      <h2 className="step-title">마지막으로 몇 가지만 더요</h2>

      <label className="field-label">신용점수(NICE 기준)</label>
      <div className="amount-input-group">
        <div className="amount-input-row">
          <input
            type="number"
            className="amount-input"
            placeholder="0"
            min={300}
            max={1000}
            value={data.credit_score || ''}
            onChange={e => {
              const v = Number(e.target.value)
              if (v >= 0 && v <= 1000) onChange({ credit_score: v })
            }}
          />
          <span className="amount-input-suffix">점</span>
        </div>
        <div className="amount-display">{data.credit_score}점</div>
        <div className="amount-chips">
          {CREDIT_PRESETS.map(score => (
            <button
              key={score}
              className={`amount-chip ${data.credit_score === score ? 'active' : ''}`}
              onClick={() => onChange({ credit_score: score })}
            >
              {score}점
            </button>
          ))}
        </div>
      </div>

      <label className="field-label">기존 월상환액</label>
      <div className="amount-input-group">
        <div className="amount-input-row">
          <input
            type="number"
            className="amount-input"
            placeholder="0"
            value={wonToMan(data.existing_debt_monthly)}
            onChange={e => onChange({ existing_debt_monthly: manToWon(e.target.value) })}
          />
          <span className="amount-input-suffix">만원</span>
        </div>
        <div className="amount-display">{formatWon(data.existing_debt_monthly)}</div>
        <div className="amount-chips">
          {DEBT_CHIPS.map(chip => (
            <button
              key={chip.label}
              className="amount-chip"
              onClick={() => onChange({ existing_debt_monthly: Math.max(0, data.existing_debt_monthly + chip.amount) })}
            >
              {chip.label}
            </button>
          ))}
          <button
            className="amount-chip amount-chip-reset"
            onClick={() => onChange({ existing_debt_monthly: 0 })}
          >
            초기화
          </button>
        </div>
      </div>

      <label className="field-label">상환 방식</label>
      <div className="radio-group">
        {(Object.entries(REPAYMENT_LABELS) as [RepaymentMethod, string][]).map(([val, label]) => (
          <button
            key={val}
            className={`radio-btn ${data.repayment_method === val ? 'active' : ''}`}
            onClick={() => onChange({ repayment_method: val })}
          >
            {label}
          </button>
        ))}
      </div>

      <label className="field-label">대출 기간</label>
      <div className="radio-group">
        {[10, 15, 20, 30, 40].map(years => (
          <button
            key={years}
            className={`radio-btn ${data.loan_term_years === years ? 'active' : ''}`}
            onClick={() => onChange({ loan_term_years: years })}
          >
            {years}년
          </button>
        ))}
      </div>

      <div className="step-buttons">
        <button className="btn btn-ghost" onClick={onBack} disabled={loading}>이전</button>
        <button className="btn btn-primary" onClick={onSubmit} disabled={loading}>
          {loading ? '계산하고 있어요...' : '계산하기'}
        </button>
      </div>
    </div>
  )
}
