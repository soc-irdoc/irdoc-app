import { useNavigate } from 'react-router-dom'
import type { Incident } from '@/types/incident'
import { SEVERITY_LABELS, SEVERITY_COLORS, STATUS_LABELS, STATUS_COLORS } from '@/types/incident'
import { ExternalRefBadge } from '@/components/common/ExternalRefBadge'
import { copyToClipboard } from '@/lib/utils'
import { useUIStore } from '@/stores/uiStore'

interface TopBarProps {
  incident: Incident
  activeSection: string
  onSectionChange: (section: string) => void
}

const SECTIONS = [
  { key: 'timeline', label: 'Timeline', icon: '⏱' },
  { key: 'iocs',     label: 'IOCs',     icon: '🔍' },
  { key: 'assets',   label: 'Assets',   icon: '🖥️' },
  { key: 'summary',  label: 'Summary',  icon: '📊' },
  { key: 'reports',  label: 'Reports',  icon: '📄' },
  { key: 'graph',    label: 'Graph',    icon: '🕸' },
]

export function TopBar({ incident, activeSection, onSectionChange }: TopBarProps) {
  const navigate = useNavigate()
  const addToast = useUIStore((s) => s.addToast)

  return (
    <div
      style={{
        background: 'var(--bg-surface)',
        borderBottom: '1px solid var(--border)',
        flexShrink: 0,
      }}
    >
      {/* Top row: incident header */}
      <div
        style={{
          height: 56,
          display: 'flex',
          alignItems: 'center',
          padding: '0 20px',
          gap: 12,
        }}
      >
        {/* Back */}
        <button
          className="icon-btn"
          onClick={() => navigate('/incidents')}
          aria-label="Back to incidents"
          title="Back to incidents"
          style={{ fontSize: 16 }}
        >
          ←
        </button>

        {/* Severity badge */}
        <span
          className={`chip ${SEVERITY_COLORS[incident.severity]}`}
          style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11 }}
        >
          {SEVERITY_LABELS[incident.severity]}
        </span>

        {/* Incident ref */}
        <span
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 12,
            color: 'var(--text-muted)',
          }}
        >
          {incident.incident_ref}
        </span>

        {/* Title */}
        <h1
          style={{
            fontSize: 17,
            fontWeight: 800,
            flex: 1,
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            color: 'var(--text-primary)',
            letterSpacing: '-0.01em',
          }}
        >
          {incident.title}
        </h1>

        {/* External refs */}
        {incident.external_refs?.map((ref) => (
          <ExternalRefBadge key={ref.id} ref={ref} />
        ))}

        {/* Status */}
        <span className={`chip ${STATUS_COLORS[incident.status]}`}>
          {STATUS_LABELS[incident.status]}
        </span>

        {/* Actions */}
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => {
              copyToClipboard(incident.incident_ref)
              addToast('Copied to clipboard', 'success')
            }}
          >
            Copy ID
          </button>
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => onSectionChange('reports')}
          >
            Report
          </button>
        </div>
      </div>

      {/* Section tabs */}
      <div
        style={{
          display: 'flex',
          gap: 0,
          padding: '0 20px',
          overflowX: 'auto',
        }}
      >
        {SECTIONS.map((sec) => (
          <button
            key={sec.key}
            onClick={() => onSectionChange(sec.key)}
            style={{
              padding: '12px 16px',
              fontSize: 13,
              fontWeight: 600,
              color: activeSection === sec.key ? 'var(--accent)' : 'var(--text-muted)',
              background: 'transparent',
              border: 'none',
              borderBottom: `2px solid ${activeSection === sec.key ? 'var(--accent)' : 'transparent'}`,
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              transition: 'all 0.15s',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              fontFamily: 'Syne, sans-serif',
            }}
          >
            {sec.icon} {sec.label}
          </button>
        ))}
      </div>
    </div>
  )
}
