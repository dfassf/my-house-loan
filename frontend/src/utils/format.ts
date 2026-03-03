export function formatLimit(value: number): string {
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

export function formatWon(value: number): string {
  return Math.round(value).toLocaleString() + '원'
}
