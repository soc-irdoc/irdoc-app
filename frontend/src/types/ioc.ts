export type IOCType = 'email' | 'domain' | 'ip' | 'url' | 'hash' | 'file' | 'username'
export type IOCStatus = 'active' | 'blocked' | 'remediated' | 'fp'
export type TLPLevel = 'white' | 'green' | 'amber' | 'red'

export interface IOC {
  id: string
  incident_id: string
  ioc_type: IOCType
  value: string
  confidence: number
  status: IOCStatus
  enrichment: Record<string, unknown>
  tlp_level: TLPLevel
  tags: string[]
  created_at: string
  updated_at: string
}

export interface CreateIOCPayload {
  ioc_type: IOCType
  value: string
  confidence?: number
  tlp_level?: TLPLevel
  tags?: string[]
}

export interface UpdateIOCPayload {
  status?: IOCStatus
  confidence?: number
  tlp_level?: TLPLevel
  tags?: string[]
}

export interface DetectedIOC {
  ioc_type: IOCType
  value: string
}

export const IOC_TYPE_ICONS: Record<IOCType, string> = {
  email:    '📧',
  domain:   '🌐',
  ip:       '🔌',
  url:      '🔗',
  hash:     '#',
  file:     '📄',
  username: '👤',
}

export const IOC_STATUS_COLORS: Record<IOCStatus, string> = {
  active:    'chip-red',
  blocked:   'chip-yellow',
  remediated:'chip-green',
  fp:        'chip-muted',
}

export const TLP_COLORS: Record<TLPLevel, string> = {
  white: 'chip-muted',
  green: 'chip-green',
  amber: 'chip-yellow',
  red:   'chip-red',
}
