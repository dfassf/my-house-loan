import type { LoanSimulationInput, RepaymentMethod } from '../types'
import { REPAYMENT_LABELS } from '../types'
import AmountInput from './AmountInput'
import type { AmountChip } from './AmountInput'

interface Props {
  data: LoanSimulationInput
  onChange: (patch: Partial<LoanSimulationInput>) => void
  onSubmit: () => void
  onBack: () => void
  loading: boolean
}

const CREDIT_PRESETS = [700, 800, 900]

const DEBT_CHIPS: AmountChip[] = [
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
      <AmountInput
        value={data.existing_debt_monthly}
        onChange={v => onChange({ existing_debt_monthly: v })}
        chips={DEBT_CHIPS}
      />

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
