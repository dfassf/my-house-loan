import { useState } from 'react'
import type { SimulationResponse, CombinationResult, LoanProductResult } from '../types'
import { calcEqualPrincipalAndInterest, calcEqualPrincipal } from '../calculator'

interface Props {
  result: SimulationResponse
  onReset: () => void
}

function formatLimit(value: number): string {
  if (value >= 100_000_000) {
    const uk = Math.floor(value / 100_000_000)
    const man = Math.floor((value % 100_000_000) / 10_000)
    return man > 0 ? `${uk}억 ${man.toLocaleString()}만원` : `${uk}억원`
  }
  if (value >= 10_000) {
    return `${Math.round(value / 10_000).toLocaleString()}만원`
  }
  return `${value.toLocaleString()}원`
}

function formatWon(value: number): string {
  return Math.round(value).toLocaleString() + '원'
}

type RepayMethod = 'annuity' | 'equal-principal'

function calcMonthly(principal: number, annualRatePct: number, method: RepayMethod, months: number = 360): number {
  if (method === 'equal-principal') {
    return calcEqualPrincipal(principal, annualRatePct, months).monthlyPayment
  }
  return calcEqualPrincipalAndInterest(principal, annualRatePct, months).monthlyPayment
}

export default function ResultPage({ result, onReset }: Props) {
  const policyProducts: LoanProductResult[] = []
  const bankProducts: LoanProductResult[] = []

  for (const combo of result.combinations) {
    for (const p of combo.products) {
      if (p.product_type === 'policy' && !policyProducts.find(x => x.product_name === p.product_name)) {
        policyProducts.push(p)
      }
      if (p.product_type === 'bank' && !bankProducts.find(x => x.product_name === p.product_name)) {
        bankProducts.push(p)
      }
    }
  }

  const hasDidimdol = policyProducts.some(p => p.product_name.includes('디딤돌'))
  const hasBogeumjari = policyProducts.some(p => p.product_name.includes('보금자리'))
  const hasBothPolicy = hasDidimdol && hasBogeumjari
  const hasAnyPolicy = hasDidimdol || hasBogeumjari
  const didimdolProduct = policyProducts.find(p => p.product_name.includes('디딤돌'))
  const bogeumjariProduct = policyProducts.find(p => p.product_name.includes('보금자리'))
  const rejections = result.policy_rejections ?? []

  type ResultType = 'both' | 'didimdol_only' | 'bogeumjari_only' | 'bank_only'
  let resultType: ResultType = 'bank_only'
  if (hasBothPolicy) resultType = 'both'
  else if (hasDidimdol) resultType = 'didimdol_only'
  else if (hasBogeumjari) resultType = 'bogeumjari_only'

  return (
    <div className="app">
      <div className="slides">
        <div className="slide result-slide active">
          <div>
            {resultType === 'both' && (
              <ResultHeader icon="🎉" color="blue" label="두 상품 모두 가능" title="비교해 보세요" />
            )}
            {resultType === 'didimdol_only' && (
              <ResultHeader icon="🏠" color="blue" label="BEST OPTION" title="디딤돌 대출" />
            )}
            {resultType === 'bogeumjari_only' && (
              <ResultHeader icon="🏡" color="green" label="RECOMMENDED" title="보금자리론" />
            )}
            {resultType === 'bank_only' && (
              <ResultHeader icon="🏦" color="grey" label="ALTERNATIVE" title="시중은행" />
            )}

            {resultType === 'both' && didimdolProduct && bogeumjariProduct && (
              <TabbedResult didimdol={didimdolProduct} bogeumjari={bogeumjariProduct} />
            )}

            {resultType === 'didimdol_only' && didimdolProduct && (
              <ProductInfoCard product={didimdolProduct} color="blue" />
            )}

            {resultType === 'bogeumjari_only' && bogeumjariProduct && (
              <>
                <ProductInfoCard product={bogeumjariProduct} color="green" />
                {rejections.length > 0 && (
                  <>
                    <div className="result-spacer" />
                    <div className="group-label">자격 검토</div>
                    <RejectionTags rejections={rejections} />
                  </>
                )}
              </>
            )}

            {resultType === 'bank_only' && (
              <>
                <div className="result-group">
                  <div className="result-tagline grey-border">
                    입력한 조건으로는 주택기금 대출을 받기 어려워요. 시중은행 대출을 확인해 보세요.
                  </div>
                </div>
                {result.combinations.length > 0 && (
                  <>
                    <div className="result-spacer" />
                    <div className="group-label">은행 대출 조합</div>
                    <BankCombinations combinations={result.combinations} />
                  </>
                )}
                {rejections.length > 0 && (
                  <>
                    <div className="result-spacer" />
                    <div className="group-label">자격 검토</div>
                    <RejectionTags rejections={rejections} />
                  </>
                )}
              </>
            )}

            {hasAnyPolicy && result.combinations.length > 0 && (
              <>
                <div className="result-spacer" />
                <div className="group-label">대출 조합</div>
                <BankCombinations combinations={result.combinations} />
              </>
            )}

            <div className="result-spacer" />
            <div className="group-label">상환방식</div>
            <RepaymentInfo />

            <div className="result-spacer" />
            <div className="group-label">주의사항</div>
            <div className="notice-list">
              <div className="notice-item">기본 LTV 70% / DTI 60%를 적용했어요. 상품과 상황에 따라 달라요.</div>
              <div className="notice-item">자세한 조건은 <strong>주택금융공사 업무처리기준</strong>에서 꼭 확인해 주세요.</div>
            </div>

            <div className="result-spacer" />
            <div className="disclaimer-section">
              <p>이 결과는 참고용이에요. 실제 대출 조건은 금융기관 심사와 신용에 따라 달라질 수 있어요.</p>
              <p>정책대출 금리와 조건은 수시로 바뀔 수 있고, 은행대출 금리는 시중 평균 추정치예요.</p>
            </div>

            <div className="result-spacer-sm" />
            <button className="btn-restart" onClick={onReset}>↩ 다시 계산하기</button>
          </div>
        </div>
      </div>
    </div>
  )
}

function ResultHeader({ icon, color, label, title }: { icon: string; color: string; label: string; title: string }) {
  return (
    <div className="result-header-area">
      <div className="result-badge-wrap">
        <div className={`result-icon ${color}`}>{icon}</div>
        <div>
          <div className={`result-option-label ${color}`}>{label}</div>
          <div className="result-title-text">{title}</div>
        </div>
      </div>
    </div>
  )
}

function ProductInfoCard({ product, color }: { product: LoanProductResult; color: 'blue' | 'green' }) {
  const [method, setMethod] = useState<RepayMethod>('annuity')
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
                className={`mc-tab${method === 'annuity' ? (color === 'green' ? ' active-green' : ' active') : ''}`}
                onClick={() => setMethod('annuity')}
              >원리금균등</button>
              <button
                className={`mc-tab${method === 'equal-principal' ? (color === 'green' ? ' active-green' : ' active') : ''}`}
                onClick={() => setMethod('equal-principal')}
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

function TabbedResult({ didimdol, bogeumjari }: { didimdol: LoanProductResult; bogeumjari: LoanProductResult }) {
  const [activeTab, setActiveTab] = useState<'didimdol' | 'bogeumjari'>('didimdol')

  return (
    <>
      <div className="result-tabs">
        <button
          className={`result-tab${activeTab === 'didimdol' ? ' active-blue' : ''}`}
          onClick={() => setActiveTab('didimdol')}
        >
          <span className="result-tab-badge blue">금리 최저</span>
          <span className="result-tab-name">디딤돌 대출</span>
          <span className="result-tab-limit">{formatLimit(didimdol.loan_amount)}</span>
        </button>
        <button
          className={`result-tab${activeTab === 'bogeumjari' ? ' active-green' : ''}`}
          onClick={() => setActiveTab('bogeumjari')}
        >
          <span className="result-tab-badge green">한도 우위</span>
          <span className="result-tab-name">보금자리론</span>
          <span className="result-tab-limit">{formatLimit(bogeumjari.loan_amount)}</span>
        </button>
      </div>
      <div className={`tab-pane${activeTab === 'didimdol' ? ' active' : ''}`}>
        <ProductInfoCard product={didimdol} color="blue" />
      </div>
      <div className={`tab-pane${activeTab === 'bogeumjari' ? ' active' : ''}`}>
        <ProductInfoCard product={bogeumjari} color="green" />
      </div>
    </>
  )
}

function RejectionTags({ rejections }: { rejections: { product_name: string; reasons: string[] }[] }) {
  return (
    <div className="result-group">
      {rejections.map((rej, i) => (
        <div key={i} className="tag-section" style={i > 0 ? { marginTop: 8 } : undefined}>
          <div className="tag-section-label">{rej.product_name} 미해당 사유</div>
          <div className="tags">
            {rej.reasons.map((r, j) => (
              <span key={j} className="tag fail">✗ {r}</span>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

function BankCombinations({ combinations }: { combinations: CombinationResult[] }) {
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

function RepaymentInfo() {
  return (
    <div className="result-group">
      <div className="repay-section">
        <div className="repay-item">
          <div className="repay-name">원리금균등분할상환</div>
          <div className="repay-desc">매달 내는 금액이 같아서 계획 세우기 좋아요.</div>
        </div>
        <div className="repay-item">
          <div className="repay-name">원금균등분할상환</div>
          <div className="repay-desc">매달 같은 원금을 갚고, 이자는 점점 줄어요. 처음엔 많이 내지만 총 이자가 가장 적어요.</div>
        </div>
        <div className="repay-item">
          <div className="repay-name">체증식 분할상환</div>
          <div className="repay-desc">처음엔 적게 내다가 점점 많아져요. 만 40세 미만이거나 공사 사전심사를 통과하면 선택할 수 있어요.</div>
        </div>
      </div>
      <div className="repay-tenure">
        <span className="repay-tenure-label">대출 만기</span>
        <span className="repay-tenure-val">10년 · 15년 · 20년 · 30년 · 40년 · 50년</span>
      </div>
    </div>
  )
}

