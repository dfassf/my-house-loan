/**
 * 프론트엔드용 상환 계산기.
 * 백엔드 repayment.py의 간소화 버전 — 월납입금/총이자 계산만.
 */

export interface QuickCalcResult {
  monthlyPayment: number
  totalInterest: number
  totalPayment: number
}

export function calcEqualPrincipalAndInterest(
  principal: number,
  annualRatePct: number,
  months: number,
): QuickCalcResult {
  if (months <= 0 || principal <= 0) {
    return { monthlyPayment: 0, totalInterest: 0, totalPayment: 0 }
  }

  const r = annualRatePct / 100 / 12

  if (r === 0) {
    const monthly = Math.round(principal / months)
    return { monthlyPayment: monthly, totalInterest: 0, totalPayment: principal }
  }

  const factor = Math.pow(1 + r, months)
  const monthly = Math.round(principal * r * factor / (factor - 1))
  const total = monthly * months
  return {
    monthlyPayment: monthly,
    totalInterest: total - principal,
    totalPayment: total,
  }
}

export function calcEqualPrincipal(
  principal: number,
  annualRatePct: number,
  months: number,
): QuickCalcResult {
  if (months <= 0 || principal <= 0) {
    return { monthlyPayment: 0, totalInterest: 0, totalPayment: 0 }
  }

  const r = annualRatePct / 100 / 12
  const basePrincipal = Math.round(principal / months)
  const firstMonthPayment = basePrincipal + Math.round(principal * r)

  // 총 이자 = sum(잔여원금 * r) for each month
  let totalInterest = 0
  let remaining = principal
  for (let i = 0; i < months; i++) {
    totalInterest += Math.round(remaining * r)
    remaining -= basePrincipal
  }

  return {
    monthlyPayment: firstMonthPayment,
    totalInterest,
    totalPayment: principal + totalInterest,
  }
}
