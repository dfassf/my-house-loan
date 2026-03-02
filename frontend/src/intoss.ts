import {
  closeView,
  getOperationalEnvironment,
  getTossShareLink,
  share,
} from '@apps-in-toss/web-framework'
import { INTOSS_APP_NAME } from './env'

type IntossEnvironment = 'web' | 'sandbox' | 'toss'

declare global {
  interface Window {
    ReactNativeWebView?: {
      postMessage: (message: string) => void
    }
    __CONSTANT_HANDLER_MAP?: Record<string, unknown>
  }
}

function hasIntossBridge(): boolean {
  if (typeof window === 'undefined') return false
  return Boolean(window.ReactNativeWebView)
}

export function getIntossEnvironment(): IntossEnvironment {
  if (!hasIntossBridge()) return 'web'

  try {
    const env = getOperationalEnvironment()
    if (env === 'toss' || env === 'sandbox') {
      return env
    }
  } catch {
    return 'web'
  }

  return 'web'
}

export function isIntossRuntime(): boolean {
  return getIntossEnvironment() !== 'web'
}

export function toIntossPath(path = ''): string {
  if (!path) return `intoss://${INTOSS_APP_NAME}`
  return `intoss://${INTOSS_APP_NAME}/${path.replace(/^\/+/, '')}`
}

export async function getTossShareLinkSafe(path: string): Promise<string | null> {
  if (!isIntossRuntime()) return null

  try {
    return await getTossShareLink(path)
  } catch {
    return null
  }
}

export async function shareInIntoss(message: string): Promise<boolean> {
  if (!isIntossRuntime()) return false

  try {
    await share({ message })
    return true
  } catch {
    return false
  }
}

export async function closeIntossViewSafe(): Promise<boolean> {
  if (!isIntossRuntime()) return false

  try {
    await closeView()
    return true
  } catch {
    return false
  }
}
