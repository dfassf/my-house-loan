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

/** 원 단위 → 한글 억/만원 표기 (입력 화면용) */
export function formatWonKorean(value: number): string {
  if (value >= 100_000_000) {
    const uk = Math.floor(value / 100_000_000)
    const man = Math.floor((value % 100_000_000) / 10_000)
    return man > 0 ? `${uk}억 ${man.toLocaleString()}만원` : `${uk}억원`
  }
  if (value >= 10_000) {
    return `${(value / 10_000).toLocaleString()}만원`
  }
  return value === 0 ? '0원' : `${value.toLocaleString()}원`
}

/** 만원 단위 문자열 → 원 단위 변환 */
export function manToWon(manStr: string): number {
  const n = parseFloat(manStr)
  return isNaN(n) ? 0 : Math.round(n * 10_000)
}

/** 원 단위 → 만원 단위 문자열 (input value용) */
export function wonToMan(won: number): string {
  const man = won / 10_000
  return man === 0 ? '' : String(man)
}
