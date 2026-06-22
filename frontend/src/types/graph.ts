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
  ioc_ip:                'input_numbers_color.svg',
  ioc_domain:            'globe_with_meridians_color.svg',
  ioc_email:             'e-mail_color.svg',
  ioc_url:               'link_color.svg',
  ioc_hash:              '#',
  ioc_file:              'page_facing_up_color.svg',
  ioc_username:          'bust_in_silhouette_color.svg',
  event:                 'pushpin_color.svg',
  evidence:              'paperclip_color.svg',
  asset_host:            'desktop_computer_color.svg',
  asset_server:          'file_cabinet_color.svg',
  asset_workstation:     'laptop_color.svg',
  asset_laptop:          'laptop_color.svg',
  asset_mobile:          'mobile_phone_color.svg',
  asset_network_device:  'globe_with_meridians_color.svg',
  asset_account:         'bust_in_silhouette_color.svg',
  asset_service_account: 'robot_color.svg',
  asset_file:            'page_facing_up_color.svg',
  asset_directory:       'file_folder_color.svg',
  asset_url:             'link_color.svg',
  asset_email_address:   'e-mail_color.svg',
  asset_database:        'card_file_box_color.svg',
  asset_application:     'gear_color.svg',
  asset_cloud_resource:  'cloud_color.svg',
  asset_other:           'package_color.svg',
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
