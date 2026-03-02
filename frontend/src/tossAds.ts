import { isIntossRuntime } from './intoss'
import { loadFullScreenAd, showFullScreenAd } from '@apps-in-toss/web-framework'

const INTERSTITIAL_TEST_ID = 'ait-ad-test-interstitial-id'
const REWARDED_TEST_ID = 'ait-ad-test-rewarded-id'

const INTERSTITIAL_ID = import.meta.env.VITE_AD_INTERSTITIAL_ID || INTERSTITIAL_TEST_ID
const REWARDED_ID = import.meta.env.VITE_AD_REWARDED_ID || REWARDED_TEST_ID

const AD_TIMEOUT_MS = 15_000

export function isAdsSupported(): boolean {
  return isIntossRuntime()
}

function withTimeout<T>(promise: Promise<T>, fallback: T): Promise<T> {
  return Promise.race([
    promise,
    new Promise<T>((resolve) => setTimeout(() => resolve(fallback), AD_TIMEOUT_MS)),
  ])
}

function runLoadAndShow(
  adGroupId: string,
  opts: { trackReward?: boolean; timeoutFallback: boolean },
): Promise<boolean | string> {
  const result = new Promise<boolean | string>((resolve) => {
    let earned = false
    const cleanupLoad = loadFullScreenAd({
      options: { adGroupId },
      onEvent: (event) => {
        if (event.type !== 'loaded') return
        cleanupLoad()
        const cleanupShow = showFullScreenAd({
          options: { adGroupId },
          onEvent: (showEvent) => {
            if (showEvent.type === 'userEarnedReward') earned = true
            if (showEvent.type === 'dismissed' || showEvent.type === 'failedToShow') {
              cleanupShow()
              resolve(opts.trackReward ? earned : true)
            }
          },
          onError: (err) => { console.warn('[ad] show error:', err); cleanupShow(); resolve(false) },
        })
      },
      onError: (err) => { cleanupLoad(); resolve(err instanceof Error ? `[ad] load: ${err.message}` : '[ad] load failed') },
    })
  })

  return withTimeout(result, opts.timeoutFallback)
}

export async function loadAndShowInterstitial(): Promise<boolean | string> {
  if (!isAdsSupported()) return false
  try {
    return runLoadAndShow(INTERSTITIAL_ID, { timeoutFallback: true })
  } catch (err) {
    console.warn('[ad] interstitial failed:', err)
    return false
  }
}

export async function loadAndShowRewarded(): Promise<boolean | string> {
  if (!isAdsSupported()) return '[ad] not intoss runtime'
  try {
    return runLoadAndShow(REWARDED_ID, { trackReward: true, timeoutFallback: false })
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    return `[ad] ${msg}`
  }
}
