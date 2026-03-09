import { useState } from 'react'
import type { LoanProductResult } from '../../types'
import { calcEqualPrincipalAndInterest, calcEqualPrincipal } from '../../calculator'
import { formatLimit, formatWon } from '../../utils/format'

type CalcTab = 'equal_principal_and_interest' | 'equal_principal'

function calcMonthly(principal: number, annualRatePct: number, method: CalcTab, months: number = 360): number {
  if (method === 'equal_principal') {
    return calcEqualPrincipal(principal, annualRatePct, months).monthlyPayment
  }
  return calcEqualPrincipalAndInterest(principal, annualRatePct, months).monthlyPayment
}

interface Props {
  product: LoanProductResult
  color: 'blue' | 'green'
}

export default function ProductInfoCard({ product, color }: Props) {
  const [method, setMethod] = useState<CalcTab>('equal_principal_and_interest')
  const months = product.loan_term_years * 12
  const monthly = calcMonthly(product.loan_amount, product.annual_rate_pct, method, months)

  return (
    <>
      <div className="result-group">
        <div className={`result-tagline${color === 'green' ? ' green-border' : ''}`}>
          {color === 'blue'
            ? '시중은행보다 훨씬 낮은 금리로 대출받을 수 있어요.'
            : 'DSR을 보지 않아서 소득이 적어도 고정금리로 많이 빌릴 수 있어요.'}
        </div>
      </div>
      <div className="result-spacer" />
      <div className="group-label">상품 정보</div>
      <div className="result-group">
        <div className="rate-limit-row">
          <div className="info-pill">
            <span className="info-pill-label">적용 금리</span>
            <span className={`info-pill-val ${color}`}>{product.annual_rate_pct}%</span>
          </div>
          <div className="info-pill">
            <span className="info-pill-label">예상 한도</span>
            <span className={`info-pill-val ${color}`}>{formatLimit(product.loan_amount)}</span>
          </div>
        </div>
      </div>
      <div className="result-spacer-sm" />
      <div className="result-group">
        <div className={`limit-detail-card ${color}-top`}>
          <div className="limit-detail-label">예상 대출 한도</div>
          <div className={`limit-detail-amount ${color}`}>{formatLimit(product.loan_amount)}</div>
          <div className="monthly-calc" style={{ marginTop: 16, borderTop: 'none', paddingTop: 0 }}>
            <div className="monthly-calc-tabs">
              <button
                className={`mc-tab${method === 'equal_principal_and_interest' ? (color === 'green' ? ' active-green' : ' active') : ''}`}
                onClick={() => setMethod('equal_principal_and_interest')}
              >원리금균등</button>
              <button
                className={`mc-tab${method === 'equal_principal' ? (color === 'green' ? ' active-green' : ' active') : ''}`}
                onClick={() => setMethod('equal_principal')}
              >원금균등</button>
            </div>
            <div className="monthly-amount-row">
              <span className="monthly-label-sm">첫 달 월 지출액</span>
              <span className={`monthly-amount ${color}`}>{formatWon(monthly)}</span>
            </div>
            <div className="monthly-calc-note">{product.loan_term_years}년 만기, 첫 달 납입금 기준이에요.</div>
          </div>
        </div>
      </div>

      {product.eligibility_notes.length > 0 && (
        <>
          <div className="result-spacer" />
          <div className="group-label">충족 조건</div>
          <div className="result-group">
            <div className="tag-section">
              <div className="tags">
                {product.eligibility_notes.map((note, i) => (
                  <span key={i} className="tag pass">✓ {note}</span>
                ))}
              </div>
            </div>
          </div>
        </>
      )}

      {product.discount_details.length > 0 && (
        <>
          <div className="result-spacer" />
          <div className="group-label">우대 금리</div>
          <div className="result-group">
            <div className="tag-section">
              <div className="tags">
                {product.discount_details.map((d, i) => (
                  <span key={i} className="tag pass">{d}</span>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </>
  )
}
