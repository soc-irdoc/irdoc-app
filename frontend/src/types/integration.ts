export type IntegrationCategory =
  | 'ti'
  | 'siem'
  | 'edr'
  | 'iam'
  | 'email'
  | 'ticketing'
  | 'comms'
  | 'storage_sync'

export interface ConfigSchemaField {
  type: 'string' | 'password' | 'select'
  label: string
  required?: boolean
  placeholder?: string
  default?: string
  options?: { value: string; label: string }[]
}

export interface Integration {
  name: string
  display_name: string
  category: IntegrationCategory
  is_premium: boolean
  icon: string
  description: string
  config_schema: Record<string, ConfigSchemaField>
  // Per-org status (populated by API)
  is_enabled: boolean
  is_configured: boolean
  last_tested: string | null
  last_test_status: 'ok' | 'fail' | null
  last_error: string | null
}

export const CATEGORY_LABELS: Record<IntegrationCategory, string> = {
  ti:           'Threat Intelligence',
  siem:         'SIEM',
  edr:          'EDR',
  iam:          'Identity & Access',
  email:        'Email Security',
  ticketing:    'Ticketing',
  comms:        'Communications',
  storage_sync: 'Storage Sync',
}

/** Sentinel alert/detection (returned by pull endpoint) */
export interface AlertCandidate {
  entry_type: string
  description: string
  occurred_at: string
  source: string
  metadata: Record<string, unknown>
}
