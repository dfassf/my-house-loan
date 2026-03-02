import { useState } from 'react'
import type { LoanSimulationInput, InputStep } from '../types'
import InputStep1 from '../components/InputStep1'
import InputStep2 from '../components/InputStep2'
import InputStep3 from '../components/InputStep3'

const DEFAULT_INPUT: LoanSimulationInput = {
  loan_purpose: 'purchase',
  desired_amount: 300_000_000,
  housing_price: 500_000_000,
  housing_type: 'apt',
  housing_area_m2: 59,
  region: 'seoul',
  annual_income: 50_000_000,
  spouse_income: 0,
  net_assets: 200_000_000,
  marital_status: 'single',
  num_children: 0,
  is_first_time_buyer: false,
  is_homeless: true,
  credit_score: 800,
  existing_debt_monthly: 0,
  repayment_method: 'equal_principal_and_interest',
  loan_term_years: 30,
}

interface Props {
  onSubmit: (input: LoanSimulationInput) => void
  loading: boolean
}

export default function InputPage({ onSubmit, loading }: Props) {
  const [step, setStep] = useState<InputStep>(1)
  const [data, setData] = useState<LoanSimulationInput>(DEFAULT_INPUT)

  function handleChange(patch: Partial<LoanSimulationInput>) {
    setData(prev => ({ ...prev, ...patch }))
  }

  return (
    <div className="input-page">
      <div className="step-indicator">
        {[1, 2, 3].map(s => (
          <div key={s} className={`step-dot ${step >= s ? 'active' : ''}`}>
            {s}
          </div>
        ))}
      </div>

      {step === 1 && (
        <InputStep1 data={data} onChange={handleChange} onNext={() => setStep(2)} />
      )}
      {step === 2 && (
        <InputStep2 data={data} onChange={handleChange} onNext={() => setStep(3)} onBack={() => setStep(1)} />
      )}
      {step === 3 && (
        <InputStep3
          data={data}
          onChange={handleChange}
          onSubmit={() => onSubmit(data)}
          onBack={() => setStep(2)}
          loading={loading}
        />
      )}
    </div>
  )
}
