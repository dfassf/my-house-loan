/**
 * 분석 이벤트 추적 (대출 시뮬레이터 도메인).
 */

const VISIT_KEY = 'daechul_visited'

type EventName =
  | 'simulation_started'
  | 'simulation_completed'
  | 'simulation_error'
  | 'input_step_changed'
  | 'combination_selected'
  | 'return_visit'
  | 'reward_ad_earned'

export function isReturnVisit(): boolean {
  try {
    if (localStorage.getItem(VISIT_KEY)) return true
    localStorage.setItem(VISIT_KEY, '1')
  } catch {
    // 스토리지 차단
  }
  return false
}

let _decisionCounter = 0

export function newSimulationId(): string {
  _decisionCounter += 1
  return `sim_${Date.now()}_${_decisionCounter}`
}

export function trackEvent(name: EventName, params?: Record<string, string | number>): void {
  if (import.meta.env.DEV) {
    console.log(`[analytics] ${name}`, params ?? '')
  }

  // GA4 등 외부 서비스 연동 시 여기에 추가
}
