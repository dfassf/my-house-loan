import { useState, useCallback, useRef, useEffect } from 'react'
import './styles.css'
import type { AppStep, LoanSimulationInput, SimulationResponse } from './types'
import * as api from './api'
import InputPage from './pages/InputPage'
import ResultPage from './pages/ResultPage'
import Loading from './components/Loading'
import { trackEvent, newSimulationId } from './analytics'
import { loadAndShowInterstitial } from './tossAds'

export default function App() {
  const [step, setStep] = useState<AppStep>('input')
  const [result, setResult] = useState<SimulationResponse | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const errorTimeoutRef = useRef<ReturnType<typeof setTimeout>>()

  const handleSubmit = useCallback(async (input: LoanSimulationInput) => {
    setError('')
    setStep('loading')
    setLoading(true)

    newSimulationId()
    trackEvent('simulation_started')

    try {
      const data = await api.simulate(input)
      setResult(data)
      setStep('result')
      trackEvent('simulation_completed')
      loadAndShowInterstitial()
    } catch (e: unknown) {
      setStep('input')
      const msg = e instanceof Error ? e.message : '오류가 발생했어요.'
      setError(msg)
      trackEvent('simulation_error')

      if (errorTimeoutRef.current) clearTimeout(errorTimeoutRef.current)
      errorTimeoutRef.current = setTimeout(() => setError(''), 5000)
    } finally {
      setLoading(false)
    }
  }, [])

  const handleReset = useCallback(() => {
    setStep('input')
    setResult(null)
    setError('')
  }, [])

  useEffect(() => {
    return () => {
      if (errorTimeoutRef.current) clearTimeout(errorTimeoutRef.current)
    }
  }, [])

  if (step === 'loading') return <Loading />

  if (step === 'result' && result) {
    return <ResultPage result={result} onReset={handleReset} />
  }

  return (
    <div className="app-container">
      <InputPage onSubmit={handleSubmit} loading={loading} />
      {error && <div className="error-msg">{error}</div>}
    </div>
  )
}
