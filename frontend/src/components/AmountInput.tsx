import { formatWonKorean, wonToMan, manToWon } from '../utils/format'

export interface AmountChip {
  label: string
  amount: number
}

interface Props {
  value: number
  onChange: (v: number) => void
  chips: AmountChip[]
  placeholder?: string
  warn?: string
}

export default function AmountInput({ value, onChange, chips, placeholder = '0', warn }: Props) {
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
      <div className="amount-display">{formatWonKorean(value)}</div>
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
