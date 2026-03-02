const QUOTA_KEY = 'ad_quota_v1'

export const DAILY_FREE_LIMIT = 3
export const DAILY_AD_BONUS_LIMIT = 5

interface QuotaData {
  date: string
  used: number
  adBonusUsed: number
}

function getTodayStr(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function loadQuota(): QuotaData {
  try {
    const raw = localStorage.getItem(QUOTA_KEY)
    if (raw) {
      const parsed: QuotaData = JSON.parse(raw)
      if (parsed.date === getTodayStr()) {
        return parsed
      }
    }
  } catch {
    // 스토리지 차단 환경
  }
  return { date: getTodayStr(), used: 0, adBonusUsed: 0 }
}

function saveQuota(data: QuotaData): void {
  try {
    localStorage.setItem(QUOTA_KEY, JSON.stringify(data))
  } catch {
    // 스토리지 차단 환경
  }
}

export function getRemainingFree(): number {
  const quota = loadQuota()
  return Math.max(0, DAILY_FREE_LIMIT - quota.used)
}

export function consumeFreeView(): boolean {
  const quota = loadQuota()
  if (quota.used < DAILY_FREE_LIMIT) {
    quota.used += 1
    saveQuota(quota)
    return true
  }
  return false
}

export function canEarnBonus(): boolean {
  const quota = loadQuota()
  return (quota.adBonusUsed ?? 0) < DAILY_AD_BONUS_LIMIT
}

export function addBonusView(): boolean {
  const quota = loadQuota()
  if ((quota.adBonusUsed ?? 0) >= DAILY_AD_BONUS_LIMIT) {
    return false
  }
  if (quota.used > 0) {
    quota.used -= 1
  }
  quota.adBonusUsed = (quota.adBonusUsed ?? 0) + 1
  saveQuota(quota)
  return true
}
