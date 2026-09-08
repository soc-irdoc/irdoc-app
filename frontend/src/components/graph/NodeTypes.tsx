/**
 * Custom React Flow node types for the investigation graph.
 * All node types share the same base layout — only icon and color differ.
 */
import { Handle, Position, type NodeProps } from '@xyflow/react'
import type { GraphNodeData } from '@/types/graph'
import { NODE_TYPE_ICONS, IOC_STATUS_COLORS, ASSET_STATUS_COLORS } from '@/types/graph'

const ENTRY_TYPE_COLORS: Record<string, string> = {
  detection:   'var(--red)',
  containment: 'var(--yellow)',
  evidence:    '#8b5cf6',
  analysis:    'var(--accent)',
  comms:       '#06b6d4',
  note:        'var(--text-muted)',
}

// ── Base Node Layout ──────────────────────────────────────────────────────────

function BaseNode({
  icon,
  label,
  color,
  subtitle,
  badge,
  selected,
}: {
  icon: string
  label: string
  color: string
  subtitle?: string
  badge?: string
  selected?: boolean
}) {
  return (
    <div
      style={{
        background: 'var(--bg-surface)',
        border: `2px solid ${selected ? 'var(--accent)' : color}`,
        borderRadius: 10,
        padding: '10px 14px',
        minWidth: 140,
        maxWidth: 200,
        boxShadow: selected ? `0 0 0 3px var(--accent-dim)` : '0 2px 8px rgba(0,0,0,0.4)',
        cursor: 'pointer',
        transition: 'border-color 0.15s, box-shadow 0.15s',
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: color }} />

      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        {icon === '#'
          ? <span style={{ fontSize: 13, fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', flexShrink: 0 }}>#</span>
          : <img src={`/icons/${icon}`} width={22} height={22} alt="" aria-hidden="true" style={{ flexShrink: 0 }} />
        }
        <div style={{ flex: 1, overflow: 'hidden' }}>
          <p
            style={{
              fontSize: 11,
              fontWeight: 700,
              color: 'var(--text-primary)',
              fontFamily: 'JetBrains Mono, monospace',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {label}
          </p>
          {subtitle && (
            <p style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>{subtitle}</p>
          )}
        </div>
        {badge && (
          <span
            style={{
              fontSize: 9,
              fontWeight: 700,
              padding: '1px 4px',
              borderRadius: 4,
              background: color,
              color: '#fff',
              flexShrink: 0,
            }}
          >
            {badge}
          </span>
        )}
      </div>

      <Handle type="source" position={Position.Bottom} style={{ background: color }} />
    </div>
  )
}

// ── IOC Node Types ────────────────────────────────────────────────────────────

function IOCNodeBase({ data, selected, nodeType }: NodeProps & { nodeType: string }) {
  const d = data as unknown as GraphNodeData
  const icon = NODE_TYPE_ICONS[nodeType] ?? '?'
  const color = IOC_STATUS_COLORS[d.status ?? 'active'] ?? '#ef4444'
  const badge = d.confidence !== undefined ? `${d.confidence}%` : undefined

  return <BaseNode icon={icon} label={d.label} color={color} subtitle={d.status} badge={badge} selected={selected} />
}

export function IOCIPNode(props: NodeProps) { return <IOCNodeBase {...props} nodeType="ioc_ip" /> }
export function IOCDomainNode(props: NodeProps) { return <IOCNodeBase {...props} nodeType="ioc_domain" /> }
export function IOCEmailNode(props: NodeProps) { return <IOCNodeBase {...props} nodeType="ioc_email" /> }
export function IOCURLNode(props: NodeProps) { return <IOCNodeBase {...props} nodeType="ioc_url" /> }
export function IOCHashNode(props: NodeProps) { return <IOCNodeBase {...props} nodeType="ioc_hash" /> }
export function IOCFileNode(props: NodeProps) { return <IOCNodeBase {...props} nodeType="ioc_file" /> }
export function IOCUsernameNode(props: NodeProps) { return <IOCNodeBase {...props} nodeType="ioc_username" /> }

// ── Event Node ────────────────────────────────────────────────────────────────

export function EventNode({ data, selected }: NodeProps) {
  const d = data as unknown as GraphNodeData
  const color = ENTRY_TYPE_COLORS[d.entry_type ?? ''] ?? 'var(--text-muted)'
  const icon = NODE_TYPE_ICONS['event']
  const subtitle = d.entry_type ? `[${d.entry_type}]` : undefined
  return <BaseNode icon={icon} label={d.label} color={color} subtitle={subtitle} selected={selected} />
}

// ── Evidence Node ─────────────────────────────────────────────────────────────

export function EvidenceNode({ data, selected }: NodeProps) {
  const d = data as unknown as GraphNodeData
  return (
    <BaseNode
      icon={NODE_TYPE_ICONS['evidence']}
      label={d.label}
      color="#8b5cf6"
      subtitle={d.sha256 ? `SHA256: ${d.sha256}` : undefined}
      selected={selected}
    />
  )
}

// ── Asset Node ────────────────────────────────────────────────────────────────

function AssetNodeBase({ data, selected, nodeType }: NodeProps & { nodeType: string }) {
  const d = data as unknown as GraphNodeData
  const icon = NODE_TYPE_ICONS[nodeType] ?? 'package_color.svg'
  const color = ASSET_STATUS_COLORS[d.status ?? 'suspected'] ?? '#f97316'
  const badge = d.criticality as string | undefined

  return (
    <BaseNode
      icon={icon}
      label={d.label}
      color={color}
      subtitle={d.status}
      badge={badge}
      selected={selected}
    />
  )
}

export function AssetHostNode(props: NodeProps) { return <AssetNodeBase {...props} nodeType="asset_host" /> }
export function AssetServerNode(props: NodeProps) { return <AssetNodeBase {...props} nodeType="asset_server" /> }
export function AssetWorkstationNode(props: NodeProps) { return <AssetNodeBase {...props} nodeType="asset_workstation" /> }
export function AssetLaptopNode(props: NodeProps) { return <AssetNodeBase {...props} nodeType="asset_laptop" /> }
export function AssetMobileNode(props: NodeProps) { return <AssetNodeBase {...props} nodeType="asset_mobile" /> }
export function AssetNetworkDeviceNode(props: NodeProps) { return <AssetNodeBase {...props} nodeType="asset_network_device" /> }
export function AssetAccountNode(props: NodeProps) { return <AssetNodeBase {...props} nodeType="asset_account" /> }
export function AssetServiceAccountNode(props: NodeProps) { return <AssetNodeBase {...props} nodeType="asset_service_account" /> }
export function AssetFileNode(props: NodeProps) { return <AssetNodeBase {...props} nodeType="asset_file" /> }
export function AssetDirectoryNode(props: NodeProps) { return <AssetNodeBase {...props} nodeType="asset_directory" /> }
export function AssetUrlNode(props: NodeProps) { return <AssetNodeBase {...props} nodeType="asset_url" /> }
export function AssetEmailAddressNode(props: NodeProps) { return <AssetNodeBase {...props} nodeType="asset_email_address" /> }
export function AssetDatabaseNode(props: NodeProps) { return <AssetNodeBase {...props} nodeType="asset_database" /> }
export function AssetApplicationNode(props: NodeProps) { return <AssetNodeBase {...props} nodeType="asset_application" /> }
export function AssetCloudResourceNode(props: NodeProps) { return <AssetNodeBase {...props} nodeType="asset_cloud_resource" /> }
export function AssetOtherNode(props: NodeProps) { return <AssetNodeBase {...props} nodeType="asset_other" /> }

// ── Node type map for React Flow ──────────────────────────────────────────────
// Not a component export, so Fast Refresh can't isolate it — the whole module
// remounts on edit here, same as any other non-component constant a React Flow
// setup needs colocated with its node components.
// eslint-disable-next-line react-refresh/only-export-components
export const NODE_TYPES = {
  ioc_ip:                IOCIPNode,
  ioc_domain:            IOCDomainNode,
  ioc_email:             IOCEmailNode,
  ioc_url:               IOCURLNode,
  ioc_hash:              IOCHashNode,
  ioc_file:              IOCFileNode,
  ioc_username:          IOCUsernameNode,
  event:                 EventNode,
  evidence:              EvidenceNode,
  asset_host:            AssetHostNode,
  asset_server:          AssetServerNode,
  asset_workstation:     AssetWorkstationNode,
  asset_laptop:          AssetLaptopNode,
  asset_mobile:          AssetMobileNode,
  asset_network_device:  AssetNetworkDeviceNode,
  asset_account:         AssetAccountNode,
  asset_service_account: AssetServiceAccountNode,
  asset_file:            AssetFileNode,
  asset_directory:       AssetDirectoryNode,
  asset_url:             AssetUrlNode,
  asset_email_address:   AssetEmailAddressNode,
  asset_database:        AssetDatabaseNode,
  asset_application:     AssetApplicationNode,
  asset_cloud_resource:  AssetCloudResourceNode,
  asset_other:           AssetOtherNode,
}
