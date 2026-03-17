import { type ReactNode } from 'react'
import { useFeatureFlags } from '@/hooks/useFeatureFlags'

interface PremiumGateProps {
  /** Feature flag key — e.g. "report_pdf_export" */
  feature?: string
  /** Alias for feature (used in Phase 3 components) */
  featureKey?: string
  children: ReactNode
}

export function PremiumGate({ feature, featureKey, children }: PremiumGateProps) {
  const { hasFeature } = useFeatureFlags()
  const key = featureKey ?? feature ?? ''

  if (hasFeature(key)) return <>{children}</>

  return (
    <div style={{ position: 'relative', display: 'contents' }}>
      <div style={{ pointerEvents: 'none', opacity: 0.4, userSelect: 'none' }}>
        {children}
      </div>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '6px',
          background: 'rgba(22,27,38,0.85)',
          backdropFilter: 'blur(4px)',
          borderRadius: '6px',
          zIndex: 10,
        }}
      >
        <span style={{ fontSize: '22px' }}>🔒</span>
        <p style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
          Premium Feature
        </p>
        <span style={{ fontSize: '11px', color: 'var(--accent)' }}>Upgrade to unlock →</span>
      </div>
    </div>
  )
}

export default PremiumGate
