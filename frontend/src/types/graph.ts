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
  ioc_ip:       '🔢',
  ioc_domain:   '🌐',
  ioc_email:    '📧',
  ioc_url:      '🔗',
  ioc_hash:     '#',
  ioc_file:     '📄',
  ioc_username: '👤',
  event:        '📌',
  evidence:     '📎',
}

export const IOC_STATUS_COLORS: Record<string, string> = {
  active:     '#ef4444',
  blocked:    '#f97316',
  remediated: '#22c55e',
  fp:         '#6b7280',
}
