export default function RepaymentInfo() {
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
