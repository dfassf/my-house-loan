import type { SimulationResponse, LoanProductResult } from '../types'
import ResultHeader from '../components/result/ResultHeader'
import ProductInfoCard from '../components/result/ProductInfoCard'
import TabbedResult from '../components/result/TabbedResult'
import RejectionTags from '../components/result/RejectionTags'
import BankCombinations from '../components/result/BankCombinations'
import RepaymentInfo from '../components/result/RepaymentInfo'

interface Props {
  result: SimulationResponse
  onReset: () => void
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

  const didimdolProduct = policyProducts.find(p => p.product_id === 'didimdol')
  const bogeumjariProduct = policyProducts.find(p => p.product_id === 'bogeumjari')
  const hasDidimdol = !!didimdolProduct
  const hasBogeumjari = !!bogeumjariProduct
  const hasBothPolicy = hasDidimdol && hasBogeumjari
  const hasAnyPolicy = hasDidimdol || hasBogeumjari
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
