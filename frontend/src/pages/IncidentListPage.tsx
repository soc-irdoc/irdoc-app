import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useIncidents, useCreateIncident, useIncidentTemplates } from '@/hooks/useIncident'
import { AppShell } from '@/components/layout/AppShell'
import { Modal } from '@/components/common/Modal'
import { Button } from '@/components/common/Button'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { EmptyState } from '@/components/common/EmptyState'
import { ExternalRefBadge } from '@/components/common/ExternalRefBadge'
import { ProgressBar } from '@/components/common/ProgressBar'
import { useUIStore } from '@/stores/uiStore'
import {
  SEVERITY_LABELS,
  SEVERITY_COLORS,
  STATUS_LABELS,
  STATUS_COLORS,
  type Severity,
  type IncidentStatus,
} from '@/types/incident'
import { formatRelative } from '@/lib/utils'

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

  const [newTitle, setNewTitle] = useState('')
  const [newSeverity, setNewSeverity] = useState<Severity>('sev2')
  const [newTemplateId, setNewTemplateId] = useState('')

  const { data, isLoading } = useIncidents({
    status: statusFilter !== 'all' ? statusFilter : undefined,
    search: search || undefined,
  })
  const incidents = data?.data ?? []

  const { data: templates = [] } = useIncidentTemplates()
  const createIncident = useCreateIncident()

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
        {/* Top bar */}
        <div
          style={{
            height: 56,
            background: 'var(--bg-surface)',
            borderBottom: '1px solid var(--border)',
            display: 'flex',
            alignItems: 'center',
            padding: '0 24px',
            gap: 16,
            flexShrink: 0,
          }}
        >
          <div
            style={{
              fontFamily: 'Syne, sans-serif',
              fontWeight: 800,
              fontSize: 18,
              color: 'var(--text-primary)',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}
          >
            <span style={{ color: 'var(--accent)' }}>⚡</span> Incidents
          </div>
          <div style={{ flex: 1 }} />
          <Button variant="accent" size="sm" onClick={() => setShowCreate(true)}>
            + New Incident
          </Button>
        </div>

        {/* Filters */}
        <div
          style={{
            background: 'var(--bg-surface)',
            borderBottom: '1px solid var(--border)',
            padding: '12px 24px',
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
              icon="⚡"
              title="No incidents"
              description="Create your first incident to get started."
              action={
                <Button variant="accent" onClick={() => setShowCreate(true)}>
                  + New Incident
                </Button>
              }
            />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {incidents.map((incident) => (
                <div
                  key={incident.id}
                  onClick={() => navigate(`/incidents/${incident.id}/timeline`)}
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
                      {/* External refs */}
                      {incident.external_refs?.map((ref) => (
                        <ExternalRefBadge
                          key={ref.id}
                          ref={ref}
                        />
                      ))}
                      <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                        {formatRelative(incident.created_at)}
                      </span>
                    </div>
                  </div>

                  {/* Status */}
                  <span
                    className={`chip ${STATUS_COLORS[incident.status]}`}
                    style={{ flexShrink: 0 }}
                  >
                    {STATUS_LABELS[incident.status]}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

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
