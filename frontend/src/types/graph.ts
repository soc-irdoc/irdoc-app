export type NodeType =
  | 'ioc_ip'
  | 'ioc_domain'
  | 'ioc_email'
  | 'ioc_url'
  | 'ioc_hash'
  | 'ioc_file'
  | 'ioc_username'
  | 'event'
  | 'evidence'
  | 'asset_host'
  | 'asset_server'
  | 'asset_workstation'
  | 'asset_laptop'
  | 'asset_mobile'
  | 'asset_network_device'
  | 'asset_account'
  | 'asset_service_account'
  | 'asset_file'
  | 'asset_directory'
  | 'asset_url'
  | 'asset_email_address'
  | 'asset_database'
  | 'asset_application'
  | 'asset_cloud_resource'
  | 'asset_other'

export interface GraphNodeData {
  [key: string]: unknown
  label: string
  // IOC nodes
  ioc_type?: string
  status?: string
  confidence?: number
  tlp?: string
  enrichment?: Record<string, unknown>
  // Event nodes
  entry_type?: string
  occurred_at?: string
  is_pinned?: boolean
  source?: string
  // Evidence nodes
  mime_type?: string
  sha256?: string
  timeline_entry_id?: string
  // Asset nodes
  asset_type?: string
  criticality?: string
  tags?: string[]
}

export interface GraphNode {
  id: string
  type: NodeType | string
  position: { x: number; y: number }
  data: GraphNodeData
  style?: Record<string, string>
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  label?: string
  animated?: boolean
  data?: { manual?: boolean; edge_id?: string }
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export const NODE_TYPE_ICONS: Record<string, string> = {
  ioc_ip:                '🔢',
  ioc_domain:            '🌐',
  ioc_email:             '📧',
  ioc_url:               '🔗',
  ioc_hash:              '#',
  ioc_file:              '📄',
  ioc_username:          '👤',
  event:                 '📌',
  evidence:              '📎',
  asset_host:            '🖥️',
  asset_server:          '🗄️',
  asset_workstation:     '💻',
  asset_laptop:          '💻',
  asset_mobile:          '📱',
  asset_network_device:  '🌐',
  asset_account:         '👤',
  asset_service_account: '🤖',
  asset_file:            '📄',
  asset_directory:       '📁',
  asset_url:             '🔗',
  asset_email_address:   '📧',
  asset_database:        '🗃️',
  asset_application:     '⚙️',
  asset_cloud_resource:  '☁️',
  asset_other:           '📦',
}

export const ASSET_STATUS_COLORS: Record<string, string> = {
  suspected:  '#f97316',
  confirmed:  '#ef4444',
  remediated: '#22c55e',
  cleared:    '#6b7280',
}

export const IOC_STATUS_COLORS: Record<string, string> = {
  active:     '#ef4444',
  blocked:    '#f97316',
  remediated: '#22c55e',
  fp:         '#6b7280',
}
