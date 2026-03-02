import { API_BASE } from './env'
import type { LoanSimulationInput, SimulationResponse } from './types'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`
  const res = await fetch(url, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  })

  if (!res.ok) {
    const body = await res.text().catch(() => '')
    throw new Error(`요청 실패 (${res.status}): ${body || res.statusText}`)
  }

  return res.json() as Promise<T>
}

export function simulate(input: LoanSimulationInput): Promise<SimulationResponse> {
  return request<SimulationResponse>('/api/simulate', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

interface ExplainResponse {
  explanation: string
}

export function explain(result: SimulationResponse): Promise<ExplainResponse> {
  return request<ExplainResponse>('/api/explain', {
    method: 'POST',
    body: JSON.stringify(result),
  })
}
