import { type ReactNode } from 'react'

interface PremiumGateProps {
  /** Feature flag key — e.g. "report_pdf_export" */
  feature?: string
  /** Alias for feature (used in Phase 3 components) */
  featureKey?: string
  children: ReactNode
}

// All features are available on the CORE plan.
// The lock overlay is preserved below (commented) and can be restored
// when premium licensing is introduced.
export function PremiumGate({ children }: PremiumGateProps) {
  return <>{children}</>
}

export default PremiumGate
