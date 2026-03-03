interface Props {
  icon: string
  color: string
  label: string
  title: string
}

export default function ResultHeader({ icon, color, label, title }: Props) {
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
