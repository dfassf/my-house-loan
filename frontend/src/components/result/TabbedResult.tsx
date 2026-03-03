import { useState } from 'react'
import type { LoanProductResult } from '../../types'
import { formatLimit } from '../../utils/format'
import ProductInfoCard from './ProductInfoCard'

interface Props {
  didimdol: LoanProductResult
  bogeumjari: LoanProductResult
}

export default function TabbedResult({ didimdol, bogeumjari }: Props) {
  const [activeTab, setActiveTab] = useState<'didimdol' | 'bogeumjari'>('didimdol')

  return (
    <>
      <div className="result-tabs">
        <button
          className={`result-tab${activeTab === 'didimdol' ? ' active-blue' : ''}`}
          onClick={() => setActiveTab('didimdol')}
        >
          <span className="result-tab-badge blue">금리 최저</span>
          <span className="result-tab-name">디딤돌 대출</span>
          <span className="result-tab-limit">{formatLimit(didimdol.loan_amount)}</span>
        </button>
        <button
          className={`result-tab${activeTab === 'bogeumjari' ? ' active-green' : ''}`}
          onClick={() => setActiveTab('bogeumjari')}
        >
          <span className="result-tab-badge green">한도 우위</span>
          <span className="result-tab-name">보금자리론</span>
          <span className="result-tab-limit">{formatLimit(bogeumjari.loan_amount)}</span>
        </button>
      </div>
      <div className={`tab-pane${activeTab === 'didimdol' ? ' active' : ''}`}>
        <ProductInfoCard product={didimdol} color="blue" />
      </div>
      <div className={`tab-pane${activeTab === 'bogeumjari' ? ' active' : ''}`}>
        <ProductInfoCard product={bogeumjari} color="green" />
      </div>
    </>
  )
}
