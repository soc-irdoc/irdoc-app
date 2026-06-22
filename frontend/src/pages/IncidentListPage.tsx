import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useIncidents, useCreateIncident, useIncidentTemplates, useUpdateIncident, useDeleteIncident } from '@/hooks/useIncident'
import { AppShell } from '@/components/layout/AppShell'
import { Modal } from '@/components/common/Modal'
import { Button } from '@/components/common/Button'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { EmptyState } from '@/components/common/EmptyState'
import { ExternalRefBadge } from '@/components/common/ExternalRefBadge'
import { useUIStore } from '@/stores/uiStore'
import { useAuthStore } from '@/stores/authStore'
import { usePermission } from '@/lib/permissions'
import {
  SEVERITY_LABELS,
  SEVERITY_COLORS,
  STATUS_LABELS,
  STATUS_COLORS,
  type Severity,
  type IncidentStatus,
  type Incident,
} from '@/types/incident'
import { formatRelative } from '@/lib/utils'

function AssigneeDisplay({ incident, onPickUp }: { incident: Incident; onPickUp: (e: React.MouseEvent) => void }) {
  const { assigned_user } = incident
  if (assigned_user) {
    const initials = assigned_user.avatar_initials
      || assigned_user.full_name.split(' ').map(p => p[0]).join('').slice(0, 2).toUpperCase()
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
        <div style={{
          width: 24, height: 24, borderRadius: '50%',
          background: 'var(--accent)', color: '#fff',
          fontSize: 10, fontWeight: 700,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0,
        }}>
          {initials}
        </div>
        <span style={{ fontSize: 12, color: 'var(--text-muted)', maxWidth: 90, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {assigned_user.full_name}
        </span>
      </div>
    )
  }
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
      <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>— Unassigned</span>
      <button
        className="btn btn-ghost btn-sm"
        onClick={onPickUp}
        style={{ fontSize: 11, padding: '2px 8px' }}
      >
        Pick up
      </button>
    </div>
  )
}

function IncidentCard({
  incident,
  onClick,
  canDelete,
  onDeleteRequest,
}: {
  incident: Incident
  onClick: () => void
  canDelete: boolean
  onDeleteRequest: (incident: Incident) => void
}) {
  const addToast = useUIStore((s) => s.addToast)
  const currentUser = useAuthStore((s) => s.user)
  const updateIncident = useUpdateIncident(incident.id)

  async function handlePickUp(e: React.MouseEvent) {
    e.stopPropagation()
    if (!currentUser) return
    try {
      await updateIncident.mutateAsync({ assigned_to: currentUser.id })
    } catch {
      addToast('Failed to pick up incident', 'error')
    }
  }

  return (
    <div
      className="animate-slide-in"
      onClick={onClick}
      style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderRadius: 12,
        padding: '16px 20px',
        cursor: 'pointer',
        transition: 'all 0.15s',
        display: 'flex',
        alignItems: 'center',
        gap: 16,
        marginBottom: 8,
      }}
      onMouseEnter={(e) => {
        const el = e.currentTarget as HTMLElement
        el.style.borderColor = 'var(--accent)'
        el.style.background = 'var(--bg-elevated)'
      }}
      onMouseLeave={(e) => {
        const el = e.currentTarget as HTMLElement
        el.style.borderColor = 'var(--border)'
        el.style.background = 'var(--bg-surface)'
      }}
    >
      {/* Severity */}
      <span
        className={`chip ${SEVERITY_COLORS[incident.severity]}`}
        style={{ fontFamily: 'JetBrains Mono, monospace', flexShrink: 0 }}
      >
        {SEVERITY_LABELS[incident.severity]}
      </span>

      {/* Ref */}
      <span
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 11,
          color: 'var(--text-muted)',
          flexShrink: 0,
        }}
      >
        {incident.incident_ref}
      </span>

      {/* Title + meta */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <p
          style={{
            fontSize: 14,
            fontWeight: 700,
            color: 'var(--text-primary)',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            marginBottom: 4,
          }}
        >
          {incident.title}
        </p>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          {incident.external_refs?.map((ref) => (
            <ExternalRefBadge key={ref.id} ref={ref} />
          ))}
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            {formatRelative(incident.created_at)}
          </span>
        </div>
      </div>

      {/* Assignee */}
      <AssigneeDisplay incident={incident} onPickUp={handlePickUp} />

      {/* Status */}
      <span className={`chip ${STATUS_COLORS[incident.status]}`} style={{ flexShrink: 0 }}>
        {STATUS_LABELS[incident.status]}
      </span>

      {canDelete && (
        <button
          className="btn btn-ghost btn-sm"
          onClick={(e) => { e.stopPropagation(); onDeleteRequest(incident) }}
          title="Delete incident"
          style={{ flexShrink: 0, padding: '2px 6px' }}
        >
          <img src="/icons/wastebasket_color.svg" width={14} height={14} alt="" aria-hidden="true" />
        </button>
      )}
    </div>
  )
}

const STATUS_TABS: Array<{ value: IncidentStatus | 'all'; label: string }> = [
  { value: 'all',        label: 'All' },
  { value: 'open',       label: 'Open' },
  { value: 'contained',  label: 'Contained' },
  { value: 'monitoring', label: 'Monitoring' },
  { value: 'closed',     label: 'Closed' },
]

const SEVERITIES: Severity[] = ['sev1', 'sev2', 'sev3', 'sev4']

export function IncidentListPage() {
  const navigate = useNavigate()
  const addToast = useUIStore((s) => s.addToast)

  const [statusFilter, setStatusFilter] = useState<IncidentStatus | 'all'>('all')
  const [search, setSearch] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [deletingIncident, setDeletingIncident] = useState<Incident | null>(null)
  const deleteIncident = useDeleteIncident()
  const canDelete = usePermission('senior_analyst')

  const [newTitle, setNewTitle] = useState('')
  const [newSeverity, setNewSeverity] = useState<Severity>('sev2')
  const [newTemplateId, setNewTemplateId] = useState('')

  const { data, isLoading } = useIncidents({
    status: statusFilter !== 'all' ? statusFilter : undefined,
    search: search || undefined,
  })
  const incidents = data?.data ?? []

  const { data: allTemplates = [] } = useIncidentTemplates()
  const templates = allTemplates.filter((t) => !t.is_hidden)
  const createIncident = useCreateIncident()

  async function handleDeleteConfirm() {
    if (!deletingIncident) return
    try {
      await deleteIncident.mutateAsync(deletingIncident.id)
      addToast('Incident deleted', 'success')
      setDeletingIncident(null)
    } catch {
      addToast('Failed to delete incident', 'error')
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    if (!newTitle.trim()) return
    try {
      const incident = await createIncident.mutateAsync({
        title: newTitle.trim(),
        severity: newSeverity,
        template_id: newTemplateId || undefined,
      })
      setShowCreate(false)
      setNewTitle('')
      setNewSeverity('sev2')
      setNewTemplateId('')
      navigate(`/incidents/${incident.id}/timeline`)
    } catch {
      addToast('Failed to create incident', 'error')
    }
  }

  return (
    <AppShell>
      <div
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          background: 'var(--bg-base)',
        }}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '24px 24px 12px',
            flexShrink: 0,
          }}
        >
          <div
            style={{
              fontFamily: 'Syne, sans-serif',
              fontWeight: 700,
              fontSize: 18,
              color: 'var(--text-primary)',
            }}
          >
            Incidents
          </div>
          <Button variant="accent" size="sm" onClick={() => setShowCreate(true)}>
            + New Incident
          </Button>
        </div>

        {/* Filters */}
        <div
          style={{
            padding: '0 24px 12px',
            display: 'flex',
            gap: 12,
            alignItems: 'center',
            flexWrap: 'wrap',
            flexShrink: 0,
          }}
        >
          <div style={{ display: 'flex', gap: 4 }}>
            {STATUS_TABS.map((tab) => (
              <button
                key={tab.value}
                onClick={() => setStatusFilter(tab.value)}
                className={`btn btn-sm ${statusFilter === tab.value ? 'btn-accent' : 'btn-ghost'}`}
              >
                {tab.label}
              </button>
            ))}
          </div>
          <input
            type="text"
            className="form-input"
            placeholder="Search incidents..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ maxWidth: 240 }}
          />
        </div>

        {/* Incident list */}
        <div style={{ flex: 1, overflowY: 'auto', padding: 24 }}>
          {isLoading ? (
            <div className="flex justify-center py-16">
              <LoadingSpinner />
            </div>
          ) : incidents.length === 0 ? (
            <EmptyState
              icon="high_voltage_color.svg"
              title="No incidents"
              description="Create your first incident to get started."
              action={
                <Button variant="accent" onClick={() => setShowCreate(true)}>
                  + New Incident
                </Button>
              }
            />
          ) : (
            <div className="stagger-list" style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {incidents.map((incident) => (
                <IncidentCard
                  key={incident.id}
                  incident={incident}
                  onClick={() => navigate(`/incidents/${incident.id}/timeline`)}
                  canDelete={canDelete}
                  onDeleteRequest={setDeletingIncident}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      <Modal open={!!deletingIncident} title="Delete Incident" onClose={() => setDeletingIncident(null)}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
            Delete{' '}
            <strong style={{ color: 'var(--text-primary)' }}>
              {deletingIncident?.incident_ref}
            </strong>
            ? This will permanently remove all timeline entries, IOCs, tasks, and
            attachments. This cannot be undone.
          </p>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <Button variant="ghost" onClick={() => setDeletingIncident(null)}>
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

      {/* Create Incident Modal */}
      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="New Incident">
        <form onSubmit={handleCreate} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <label
              style={{
                fontSize: 11,
                fontWeight: 600,
                color: 'var(--text-muted)',
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
                marginBottom: 6,
                display: 'block',
              }}
            >
              Title
            </label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. Phishing campaign targeting finance team"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              required
              autoFocus
            />
          </div>

          <div>
            <label
              style={{
                fontSize: 11,
                fontWeight: 600,
                color: 'var(--text-muted)',
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
                marginBottom: 6,
                display: 'block',
              }}
            >
              Severity
            </label>
            <div style={{ display: 'flex', gap: 8 }}>
              {SEVERITIES.map((sev) => (
                <button
                  key={sev}
                  type="button"
                  onClick={() => setNewSeverity(sev)}
                  className={`btn btn-sm ${newSeverity === sev ? 'btn-accent' : 'btn-ghost'}`}
                >
                  {SEVERITY_LABELS[sev]}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label
              style={{
                fontSize: 11,
                fontWeight: 600,
                color: 'var(--text-muted)',
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
                marginBottom: 6,
                display: 'block',
              }}
            >
              Template (optional)
            </label>
            <div className="select-wrap">
              <select
                className="form-input"
                value={newTemplateId}
                onChange={(e) => setNewTemplateId(e.target.value)}
                style={{ fontFamily: 'Syne, sans-serif' }}
              >
                <option value="">No template</option>
                {templates.map((t) => (
                  <option key={t.id} value={t.id}>{t.name}</option>
                ))}
              </select>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 8 }}>
            <Button variant="ghost" type="button" onClick={() => setShowCreate(false)}>
              Cancel
            </Button>
            <Button variant="accent" type="submit" loading={createIncident.isPending} disabled={!newTitle.trim()}>
              Create Incident
            </Button>
          </div>
        </form>
      </Modal>
    </AppShell>
  )
}
