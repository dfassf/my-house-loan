import type { CombinationResult } from '../types'
import { REPAYMENT_LABELS } from '../types'
import type { RepaymentMethod } from '../types'

interface Props {
  combo: CombinationResult
  isTop?: boolean
}

function formatWon(value: number): string {
  if (value >= 100_000_000) {
    const uk = Math.floor(value / 100_000_000)
    const man = Math.floor((value % 100_000_000) / 10_000)
    return man > 0 ? `${uk}억 ${man.toLocaleString()}만` : `${uk}억`
  }
  return `${Math.round(value / 10_000).toLocaleString()}만`
}

export default function CombinationCard({ combo, isTop }: Props) {
  return (
    <div className={`combo-card ${isTop ? 'combo-card-top' : ''}`}>
      <div className="combo-header">
        <span className="combo-rank">{combo.rank}순위</span>
        <span className="combo-label">{combo.label}</span>
      </div>

      <div className="combo-summary">
        <div className="summary-item">
          <span className="summary-label">총 대출</span>
          <span className="summary-value">{formatWon(combo.total_loan_amount)}원</span>
        </div>
        <div className="summary-item">
          <span className="summary-label">월 납입</span>
          <span className="summary-value highlight">{formatWon(combo.total_monthly_payment)}원</span>
        </div>
        <div className="summary-item">
          <span className="summary-label">가중평균금리</span>
          <span className="summary-value">{combo.weighted_avg_rate}%</span>
        </div>
        <div className="summary-item">
          <span className="summary-label">총 이자</span>
          <span className="summary-value">{formatWon(combo.total_interest)}원</span>
        </div>
      </div>

      <div className="combo-regulation">
        <span>LTV {combo.ltv_ratio}%</span>
        <span>DSR {combo.dsr_ratio}%</span>
      </div>

      <div className="combo-products">
        {combo.products.map((product, idx) => (
          <div key={idx} className={`product-item ${product.product_type}`}>
            <div className="product-header">
              <span className={`product-badge ${product.product_type}`}>
                {product.product_type === 'policy' ? '정책' : '은행'}
              </span>
              <span className="product-name">{product.product_name}</span>
            </div>
            <div className="product-details">
              <span>대출 {formatWon(product.loan_amount)}원</span>
              <span>금리 {product.annual_rate_pct}%</span>
              <span>월 {formatWon(product.monthly_payment)}원</span>
              <span>{REPAYMENT_LABELS[product.repayment_method as RepaymentMethod] ?? product.repayment_method}</span>
            </div>
            {product.discount_details.length > 0 && (
              <div className="product-discounts">
                {product.discount_details.map((d, i) => (
                  <span key={i} className="discount-tag">{d}</span>
                ))}
              </div>
            )}
            {product.eligibility_notes.length > 0 && (
              <div className="product-notes">
                {product.eligibility_notes.map((n, i) => (
                  <p key={i} className="note-text">{n}</p>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
