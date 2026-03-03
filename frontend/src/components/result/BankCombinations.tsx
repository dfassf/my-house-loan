import type { CombinationResult } from '../../types'
import { formatLimit, formatWon } from '../../utils/format'

interface Props {
  combinations: CombinationResult[]
}

export default function BankCombinations({ combinations }: Props) {
  return (
    <div className="combo-cards">
      {combinations.map(combo => (
        <div key={combo.rank} className={`combo-card${combo.rank === 1 ? ' combo-card-top' : ''}`}>
          <div className="combo-header">
            <span className="combo-rank">{combo.rank}순위</span>
            <span className="combo-label">{combo.label}</span>
          </div>
          <div className="combo-summary">
            <div className="summary-item">
              <span className="summary-label">총 대출</span>
              <span className="summary-value">{formatLimit(combo.total_loan_amount)}</span>
            </div>
            <div className="summary-item">
              <span className="summary-label">월 납입</span>
              <span className="summary-value highlight">{formatWon(combo.total_monthly_payment)}</span>
            </div>
            <div className="summary-item">
              <span className="summary-label">금리</span>
              <span className="summary-value">{combo.weighted_avg_rate}%</span>
            </div>
            <div className="summary-item">
              <span className="summary-label">DSR</span>
              <span className="summary-value">{combo.dsr_ratio}%</span>
            </div>
          </div>
          <div className="combo-products">
            {combo.products.map((p, idx) => (
              <div key={idx} className={`product-item ${p.product_type}`}>
                <div className="product-header">
                  <span className={`product-badge ${p.product_type}`}>
                    {p.product_type === 'policy' ? '정책' : '은행'}
                  </span>
                  <span className="product-name">{p.product_name}</span>
                </div>
                <div className="product-details">
                  <span>{formatLimit(p.loan_amount)}</span>
                  <span>{p.annual_rate_pct}%</span>
                  <span>월 {formatWon(p.monthly_payment)}</span>
                </div>
                {p.discount_details.length > 0 && (
                  <div className="product-discounts">
                    {p.discount_details.map((d, j) => (
                      <span key={j} className="discount-tag">{d}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
