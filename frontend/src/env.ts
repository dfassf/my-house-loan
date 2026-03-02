const DEFAULT_SITE_URL = 'https://daechul-recommend.vercel.app'
const DEFAULT_INTOSS_APP_NAME = 'my-house-loan'

function trimTrailingSlash(url: string): string {
  return url.replace(/\/+$/, '')
}

export const API_BASE = (import.meta.env.VITE_API_URL || '').trim()
export const SITE_URL = trimTrailingSlash(import.meta.env.VITE_SITE_URL || DEFAULT_SITE_URL)
export const SITE_HOST = SITE_URL.replace(/^https?:\/\//, '')

export const INTOSS_APP_NAME = (
  import.meta.env.VITE_INTOSS_APP_NAME ||
  DEFAULT_INTOSS_APP_NAME
).trim() || DEFAULT_INTOSS_APP_NAME

export const ENABLE_ADFIT = import.meta.env.VITE_ENABLE_ADFIT !== 'false'
