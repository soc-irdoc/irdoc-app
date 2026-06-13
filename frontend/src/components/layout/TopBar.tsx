import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { Incident, Severity, IncidentStatus } from '@/types/incident'
import { SEVERITY_COLORS, STATUS_COLORS } from '@/types/incident'
import { ExternalRefBadge } from '@/components/common/ExternalRefBadge'
import { copyToClipboard } from '@/lib/utils'
import { useUIStore, type PresenceUser } from '@/stores/uiStore'
import { useAuthStore } from '@/stores/authStore'
import { useUpdateIncident } from '@/hooks/useIncident'
import { useOrgUsers } from '@/hooks/useOrgUsers'
import { usePermission } from '@/lib/permissions'
import { useDeleteIncident } from '@/hooks/useIncident'
import { Modal } from '@/components/common/Modal'
import { Button } from '@/components/common/Button'

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

function PresenceAvatars({ incidentId }: { incidentId: string }) {
  const currentUser = useAuthStore((s) => s.user)
  const presence = useUIStore((s) => s.incidentPresence[incidentId] ?? [])
  const others = presence.filter((u) => u.id !== currentUser?.id)
  if (others.length === 0) return null

  const visible = others.slice(0, 4)
  const overflow = others.length - visible.length

  const COLORS = ['#f97316', '#3b82f6', '#8b5cf6', '#10b981', '#ec4899']

  return (
    <div
      style={{ display: 'flex', alignItems: 'center', gap: 2, flexShrink: 0 }}
      title={others.map((u) => u.full_name).join(', ')}
    >
      <span style={{ fontSize: 10, color: 'var(--text-muted)', marginRight: 4 }}>Also viewing:</span>
      {visible.map((u, i) => (
        <div
          key={u.id}
          title={u.full_name}
          style={{
            width: 24, height: 24, borderRadius: '50%',
            background: COLORS[i % COLORS.length],
            color: '#fff',
            fontSize: 9, fontWeight: 700,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0,
            marginLeft: i > 0 ? -6 : 0,
            border: '2px solid var(--bg-surface)',
            cursor: 'default',
          }}
        >
          {u.avatar_initials || u.full_name.split(' ').map((p: string) => p[0]).join('').slice(0, 2).toUpperCase()}
        </div>
      ))}
      {overflow > 0 && (
        <div
          style={{
            width: 24, height: 24, borderRadius: '50%',
            background: 'var(--bg-elevated)',
            border: '2px solid var(--border)',
            color: 'var(--text-muted)',
            fontSize: 9, fontWeight: 700,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            marginLeft: -6,
          }}
        >
          +{overflow}
        </div>
      )}
    </div>
  )
}

export function TopBar({ incident, activeSection, onSectionChange }: TopBarProps) {
  const navigate = useNavigate()
  const addToast = useUIStore((s) => s.addToast)
  const updateIncident = useUpdateIncident(incident.id)
  const { data: orgUsers = [] } = useOrgUsers()
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const deleteIncident = useDeleteIncident()
  const canDelete = usePermission('senior_analyst')

  async function handleSeverityChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const severity = e.target.value as Severity
    try {
      await updateIncident.mutateAsync({ severity })
    } catch {
      addToast('Failed to update severity', 'error')
    }
  }

  async function handleStatusChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const status = e.target.value as IncidentStatus
    try {
      await updateIncident.mutateAsync({ status })
    } catch {
      addToast('Failed to update status', 'error')
    }
  }

  async function handleAssigneeChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const assigned_to = e.target.value || null
    try {
      await updateIncident.mutateAsync({ assigned_to })
    } catch {
      addToast('Failed to update assignee', 'error')
    }
  }

  async function handleDeleteConfirm() {
    try {
      await deleteIncident.mutateAsync(incident.id)
      addToast('Incident deleted', 'success')
      navigate('/incidents')
    } catch {
      addToast('Failed to delete incident', 'error')
    }
  }

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
        <select
          className={`chip ${SEVERITY_COLORS[incident.severity]}`}
          value={incident.severity}
          onChange={handleSeverityChange}
          disabled={updateIncident.isPending}
          aria-label="Change severity"
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 11,
            cursor: 'pointer',
            appearance: 'none',
            paddingRight: 6,
          }}
        >
          <option value="sev1">SEV-1</option>
          <option value="sev2">SEV-2</option>
          <option value="sev3">SEV-3</option>
          <option value="sev4">SEV-4</option>
        </select>

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
        <select
          className={`chip ${STATUS_COLORS[incident.status]}`}
          value={incident.status}
          onChange={handleStatusChange}
          disabled={updateIncident.isPending}
          aria-label="Change status"
          style={{ cursor: 'pointer', appearance: 'none', paddingRight: 6, flexShrink: 0 }}
        >
          <option value="open">OPEN</option>
          <option value="contained">CONTAINED</option>
          <option value="monitoring">MONITORING</option>
          <option value="closed">CLOSED</option>
        </select>

        {/* Assignee */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
          {incident.assigned_user && (
            <div style={{
              width: 22, height: 22, borderRadius: '50%',
              background: 'var(--accent)', color: '#fff',
              fontSize: 9, fontWeight: 700,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0,
            }}>
              {incident.assigned_user.avatar_initials
                || incident.assigned_user.full_name.split(' ').map(p => p[0]).join('').slice(0, 2).toUpperCase()}
            </div>
          )}
          <select
            className="chip chip-muted"
            value={incident.assigned_to ?? ''}
            onChange={handleAssigneeChange}
            disabled={updateIncident.isPending}
            aria-label="Change assignee"
            style={{ cursor: 'pointer', appearance: 'none', paddingRight: 6, maxWidth: 130 }}
          >
            <option value="">— Unassigned</option>
            {orgUsers.map((u) => (
              <option key={u.id} value={u.id}>{u.full_name}</option>
            ))}
          </select>
        </div>

        {/* Presence */}
        <PresenceAvatars incidentId={incident.id} />

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
          {canDelete && (
            <button
              className="btn btn-ghost btn-sm"
              onClick={() => setShowDeleteModal(true)}
              title="Delete incident"
              style={{ fontSize: 14, padding: '4px 8px' }}
            >
              🗑
            </button>
          )}
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

      <Modal open={showDeleteModal} title="Delete Incident" onClose={() => setShowDeleteModal(false)}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
            Delete{' '}
            <strong style={{ color: 'var(--text-primary)' }}>
              {incident.incident_ref}
            </strong>
            ? This will permanently remove all timeline entries, IOCs, tasks, and
            attachments. This cannot be undone.
          </p>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <Button variant="ghost" onClick={() => setShowDeleteModal(false)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={handleDeleteConfirm}
              loading={deleteIncident.isPending}
              disabled={deleteIncident.isPending}
            >
              Delete
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
