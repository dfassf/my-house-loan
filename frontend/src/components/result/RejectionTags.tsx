interface Props {
  rejections: { product_name: string; reasons: string[] }[]
}

export default function RejectionTags({ rejections }: Props) {
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
