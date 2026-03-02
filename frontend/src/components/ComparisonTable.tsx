import type { CombinationResult } from '../types'

interface Props {
  combinations: CombinationResult[]
}

function formatWon(value: number): string {
  if (value >= 100_000_000) {
    const uk = Math.floor(value / 100_000_000)
    const man = Math.floor((value % 100_000_000) / 10_000)
    return man > 0 ? `${uk}억 ${man.toLocaleString()}만` : `${uk}억`
  }
  return `${Math.round(value / 10_000).toLocaleString()}만`
}

export default function ComparisonTable({ combinations }: Props) {
  if (combinations.length === 0) return null

  return (
    <div className="comparison-table-wrapper">
      <table className="comparison-table">
        <thead>
          <tr>
            <th>순위</th>
            <th>조합</th>
            <th>금리</th>
            <th>월납입</th>
            <th>총이자</th>
            <th>DSR</th>
          </tr>
        </thead>
        <tbody>
          {combinations.map(combo => (
            <tr key={combo.rank}>
              <td className="rank-cell">{combo.rank}</td>
              <td className="label-cell">{combo.label}</td>
              <td>{combo.weighted_avg_rate}%</td>
              <td>{formatWon(combo.total_monthly_payment)}원</td>
              <td>{formatWon(combo.total_interest)}원</td>
              <td className={combo.dsr_ratio > 40 ? 'warning' : ''}>{combo.dsr_ratio}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
