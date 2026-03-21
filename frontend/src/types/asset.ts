export type AssetType =
  | 'host'
  | 'server'
  | 'workstation'
  | 'laptop'
  | 'mobile'
  | 'network_device'
  | 'account'
  | 'service_account'
  | 'file'
  | 'directory'
  | 'url'
  | 'email_address'
  | 'database'
  | 'application'
  | 'cloud_resource'
  | 'other'

export type AssetStatus = 'suspected' | 'confirmed' | 'remediated' | 'cleared'
export type AssetCriticality = 'critical' | 'high' | 'medium' | 'low'

export type AssetLinkType =
  | 'communicates_with'
  | 'owns'
  | 'runs'
  | 'connects_to'
  | 'authenticates_to'
  | 'contains'
  | 'accesses'
  | 'lateral_movement'
  | 'exfiltration_target'
  | 'related'

export interface Asset {
  id: string
  incident_id: string
  asset_type: AssetType
  name: string
  description: string | null
  status: AssetStatus
  criticality: AssetCriticality
  tags: string[]
  metadata: Record<string, unknown>
  added_by: string | null
  created_at: string
  updated_at: string
}

export interface AssetLink {
  id: string
  incident_id: string
  source_id: string
  target_id: string
  link_type: AssetLinkType
  label: string | null
  created_by: string | null
  created_at: string
}

// ── Display helpers ───────────────────────────────────────────────────────────

export const ASSET_TYPE_ICONS: Record<AssetType, string> = {
  host: '🖥️',
  server: '🗄️',
  workstation: '💻',
  laptop: '💻',
  mobile: '📱',
  network_device: '🌐',
  account: '👤',
  service_account: '🤖',
  file: '📄',
  directory: '📁',
  url: '🔗',
  email_address: '📧',
  database: '🗃️',
  application: '⚙️',
  cloud_resource: '☁️',
  other: '📦',
}

export const ASSET_TYPE_LABELS: Record<AssetType, string> = {
  host: 'Host',
  server: 'Server',
  workstation: 'Workstation',
  laptop: 'Laptop',
  mobile: 'Mobile Device',
  network_device: 'Network Device',
  account: 'User Account',
  service_account: 'Service Account',
  file: 'File',
  directory: 'Directory',
  url: 'URL',
  email_address: 'Email Address',
  database: 'Database',
  application: 'Application',
  cloud_resource: 'Cloud Resource',
  other: 'Other',
}

export const ASSET_STATUS_COLORS: Record<AssetStatus, string> = {
  suspected: 'chip-yellow',
  confirmed: 'chip-red',
  remediated: 'chip-green',
  cleared: 'chip-muted',
}

export const ASSET_CRITICALITY_COLORS: Record<AssetCriticality, string> = {
  critical: 'chip-red',
  high: 'chip-yellow',
  medium: 'chip-blue',
  low: 'chip-muted',
}

export const ASSET_LINK_TYPE_LABELS: Record<AssetLinkType, string> = {
  communicates_with: 'Communicates with',
  owns: 'Owns',
  runs: 'Runs',
  connects_to: 'Connects to',
  authenticates_to: 'Authenticates to',
  contains: 'Contains',
  accesses: 'Accesses',
  lateral_movement: 'Lateral movement to',
  exfiltration_target: 'Exfiltration target',
  related: 'Related to',
}

export const ASSET_TYPES_LIST: AssetType[] = [
  'host', 'server', 'workstation', 'laptop', 'mobile', 'network_device',
  'account', 'service_account', 'file', 'directory', 'url', 'email_address',
  'database', 'application', 'cloud_resource', 'other',
]

export const ASSET_LINK_TYPES_LIST: AssetLinkType[] = [
  'communicates_with', 'owns', 'runs', 'connects_to', 'authenticates_to',
  'contains', 'accesses', 'lateral_movement', 'exfiltration_target', 'related',
]
