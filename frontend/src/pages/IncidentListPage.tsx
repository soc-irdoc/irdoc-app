import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useIncidents, useCreateIncident, useIncidentTemplates, useUpdateIncident, useDeleteIncident } from '@/hooks/useIncident'
import { AppShell } from '@/components/layout/AppShell'
import { Modal } from '@/components/common/Modal'
import { Button } from '@/components/common/Button'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { EmptyState } from '@/components/common/EmptyState'
import { ExternalRefBadge } from '@/components/common/ExternalRefBadge'
import { Pagination } from '@/components/common/Pagination'
import { useUIStore } from '@/stores/uiStore'
import { useAuthStore } from '@/stores/authStore'
import { usePermission } from '@/lib/permissions'
import {
  DISPOSITION_COLORS,
  DISPOSITION_LABELS,
  DISPOSITION_SHORT_LABELS,
  SEVERITIES,
  SEVERITY_LABELS,
  SEVERITY_COLORS,
  STATUS_LABELS,
  STATUS_COLORS,
  type Severity,
  type IncidentStatus,
  type Incident,
} from '@/types/incident'
import {
  FIRST_CLICK_ORDER,
  PAGE_SIZES,
  parseListQuery,
  rememberListQuery,
  toApiParams,
  toSearchParams,
  type IncidentListQuery,
  type IncidentSortKey,
  type SortOrder,
} from '@/lib/incidentListQuery'
import { formatDateTime, formatRelative } from '@/lib/utils'
import { FaArrowDown, FaArrowUp, FaBolt, FaHandPointUp, FaTrashCan } from 'react-icons/fa6'

function AssigneeDisplay({ incident, onPickUp }: { incident: Incident; onPickUp: (e: React.MouseEvent) => void }) {
  const { assigned_user } = incident
  if (assigned_user) {
    const initials = assigned_user.avatar_initials
      || assigned_user.full_name.split(' ').map(p => p[0]).join('').slice(0, 2).toUpperCase()
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, minWidth: 0 }} title={assigned_user.full_name}>
        <div style={{
          width: 24, height: 24, borderRadius: '50%',
          background: 'var(--accent)', color: '#fff',
          fontSize: 10, fontWeight: 700,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0,
        }}>
          {initials}
        </div>
        <span className="incident-owner-name incident-truncate" style={{ fontSize: 12, color: 'var(--text-muted)' }}>
          {assigned_user.full_name}
        </span>
      </div>
    )
  }
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6, minWidth: 0 }}>
      <span className="incident-owner-name" style={{ fontSize: 12, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
        - Unassigned
      </span>
      <button
        className="btn btn-ghost btn-sm"
        onClick={onPickUp}
        title="Pick up"
        style={{ fontSize: 11, padding: '2px 8px', flexShrink: 0 }}
      >
        <FaHandPointUp size={10} aria-hidden="true" />
        <span className="incident-pickup-label">Pick up</span>
      </button>
    </div>
  )
}

// One row of the incidents list. Shares the .incident-grid template with the
// header, so every column lines up across rows (#126).
function IncidentRow({
  incident,
  onOpen,
  canDelete,
  onDeleteRequest,
}: {
  incident: Incident
  onOpen: () => void
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
      className="incident-row incident-grid animate-slide-in"
      role="link"
      tabIndex={0}
      onClick={onOpen}
      onKeyDown={(e) => {
        if (e.key === 'Enter' && e.target === e.currentTarget) onOpen()
      }}
    >
      {/* Severity */}
      <div className="incident-cell-sev">
        <span className={`chip chip-fixed ${SEVERITY_COLORS[incident.severity]}`}>
          {SEVERITY_LABELS[incident.severity]}
        </span>
      </div>

      {/* Ref */}
      <span
        className="incident-cell-ref incident-truncate"
        style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: 'var(--text-muted)' }}
      >
        {incident.incident_ref}
      </span>

      {/* Title + created */}
      <div className="incident-cell-title" style={{ minWidth: 0 }}>
        <p
          className="incident-truncate"
          title={incident.title}
          style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 4 }}
        >
          {incident.title}
        </p>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 0, overflow: 'hidden' }}>
          {incident.external_refs?.map((ref) => (
            <ExternalRefBadge key={ref.id} externalRef={ref} />
          ))}
          <span
            style={{ fontSize: 12, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}
            title={formatDateTime(incident.created_at)}
          >
            {formatRelative(incident.created_at)}
          </span>
        </div>
      </div>

      {/* Owner */}
      <div className="incident-cell-owner" style={{ minWidth: 0 }}>
        <AssigneeDisplay incident={incident} onPickUp={handlePickUp} />
      </div>

      {/* Status, with the final disposition below it (#124) */}
      <div className="incident-cell-status incident-cell-center">
        <span className={`chip chip-fixed ${STATUS_COLORS[incident.status]}`}>
          {STATUS_LABELS[incident.status]}
        </span>
        {incident.disposition && (
          <span
            className={`chip ${DISPOSITION_COLORS[incident.disposition]}`}
            title={DISPOSITION_LABELS[incident.disposition]}
            style={{ fontSize: 9, maxWidth: '100%', overflow: 'hidden', textOverflow: 'ellipsis' }}
          >
            {DISPOSITION_SHORT_LABELS[incident.disposition]}
          </span>
        )}
      </div>

      {/* Actions */}
      <div className="incident-cell-actions" style={{ display: 'flex', justifyContent: 'flex-end' }}>
        {canDelete && (
          <button
            className="btn btn-ghost btn-sm"
            onClick={(e) => { e.stopPropagation(); onDeleteRequest(incident) }}
            title="Delete incident"
            aria-label={`Delete ${incident.incident_ref}`}
            style={{ padding: '2px 6px' }}
          >
            <FaTrashCan size={14} aria-hidden="true" />
          </button>
        )}
      </div>
    </div>
  )
}

const SORT_COLUMNS: Array<{ key: IncidentSortKey; label: string }> = [
  { key: 'severity', label: 'Severity' },
  { key: 'ref', label: 'ID' },
  { key: 'title', label: 'Title' },
  { key: 'owner', label: 'Owner' },
  { key: 'status', label: 'Status' },
]

function SortButton({
  column,
  label,
  query,
  onSort,
}: {
  column: IncidentSortKey
  label: string
  query: IncidentListQuery
  onSort: (column: IncidentSortKey) => void
}) {
  const active = query.sort === column
  const Arrow = query.order === 'asc' ? FaArrowUp : FaArrowDown
  return (
    <button
      type="button"
      className="incident-sort-btn"
      data-active={active}
      onClick={() => onSort(column)}
      title={`Sort by ${label.toLowerCase()}`}
      aria-label={
        active
          ? `${label}, sorted ${query.order === 'asc' ? 'ascending' : 'descending'}. Click to reverse.`
          : `Sort by ${label.toLowerCase()}`
      }
    >
      {label}
      {active && <Arrow size={9} aria-hidden="true" />}
    </button>
  )
}

// Column headers; click to sort, click again to reverse (#128).
function IncidentListHeader({ query, onSort }: { query: IncidentListQuery; onSort: (column: IncidentSortKey) => void }) {
  return (
    <div className="incident-list-header incident-grid">
      {SORT_COLUMNS.map(({ key, label }) => (
        <div
          key={key}
          style={{
            display: 'flex',
            gap: 10,
            minWidth: 0,
            justifyContent: key === 'status' ? 'center' : undefined,
          }}
        >
          <SortButton column={key} label={label} query={query} onSort={onSort} />
          {/* The created time sits under the title, so it sorts from here */}
          {key === 'title' && (
            <>
              <span aria-hidden="true">/</span>
              <SortButton column="created" label="Created" query={query} onSort={onSort} />
            </>
          )}
        </div>
      ))}
      <div />
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

export function IncidentListPage() {
  const navigate = useNavigate()
  const addToast = useUIStore((s) => s.addToast)
  const [searchParams, setSearchParams] = useSearchParams()

  // Page, page size, filter, search and sort live in the URL (#127, #128).
  const query = useMemo(() => parseListQuery(searchParams), [searchParams])
  const [searchInput, setSearchInput] = useState(query.search)

  const [showCreate, setShowCreate] = useState(false)
  const [deletingIncident, setDeletingIncident] = useState<Incident | null>(null)
  const deleteIncident = useDeleteIncident()
  const canDelete = usePermission('senior_analyst')

  const [newTitle, setNewTitle] = useState('')
  const [newSeverity, setNewSeverity] = useState<Severity>('high')
  const [newTemplateId, setNewTemplateId] = useState('')

  const { data, isLoading, isFetching } = useIncidents(toApiParams(query))
  const incidents = data?.data ?? []
  const total = data?.meta?.total ?? 0

  const { data: allTemplates = [] } = useIncidentTemplates()
  const templates = allTemplates.filter((t) => !t.is_hidden)
  const createIncident = useCreateIncident()

  const updateQuery = useCallback(
    (patch: Partial<IncidentListQuery>, { replace = false } = {}) => {
      // Anything but a page change starts again from page 1.
      const next = { ...query, page: 1, ...patch }
      setSearchParams(toSearchParams(next), { replace })
    },
    [query, setSearchParams],
  )

  // "Back" from an incident returns to this view.
  useEffect(() => {
    rememberListQuery(searchParams.toString())
  }, [searchParams])

  // The URL changed from outside (back/forward, a link): follow it.
  useEffect(() => {
    setSearchInput(query.search)
  }, [query.search])

  // Search is debounced, and doesn't add a history entry per keystroke.
  useEffect(() => {
    if (searchInput.trim() === query.search) return
    const t = setTimeout(() => updateQuery({ search: searchInput.trim() }, { replace: true }), 300)
    return () => clearTimeout(t)
  }, [searchInput, query.search, updateQuery])

  // Past the last page (e.g. after deleting its only incident): go to the last page.
  useEffect(() => {
    if (!data || isFetching) return
    const lastPage = Math.max(1, Math.ceil(total / query.perPage))
    if (query.page > lastPage) updateQuery({ page: lastPage }, { replace: true })
  }, [data, isFetching, total, query.page, query.perPage, updateQuery])

  function handleSort(column: IncidentSortKey) {
    const order: SortOrder =
      query.sort === column ? (query.order === 'asc' ? 'desc' : 'asc') : FIRST_CLICK_ORDER[column]
    updateQuery({ sort: column, order })
  }

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
      setNewSeverity('high')
      setNewTemplateId('')
      navigate(`/incidents/${incident.id}/timeline`)
    } catch {
      addToast('Failed to create incident', 'error')
    }
  }

  const filtered = query.status !== 'all' || query.search !== ''

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
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
            {STATUS_TABS.map((tab) => (
              <button
                key={tab.value}
                onClick={() => updateQuery({ status: tab.value })}
                className={`btn btn-sm ${query.status === tab.value ? 'btn-accent' : 'btn-ghost'}`}
                aria-pressed={query.status === tab.value}
              >
                {tab.label}
              </button>
            ))}
          </div>
          <input
            type="search"
            className="form-input"
            placeholder="Search incidents..."
            aria-label="Search incidents"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            style={{ maxWidth: 240 }}
          />
        </div>

        {/* Incident list */}
        <div className="incident-list" style={{ flex: 1, overflowY: 'auto', padding: '12px 24px 24px' }}>
          {isLoading ? (
            <div className="flex justify-center py-16">
              <LoadingSpinner />
            </div>
          ) : incidents.length === 0 && !filtered ? (
            <EmptyState
              icon={FaBolt}
              title="No incidents"
              description="Create your first incident to get started."
              action={
                <Button variant="accent" onClick={() => setShowCreate(true)}>
                  + New Incident
                </Button>
              }
            />
          ) : (
            <>
              <IncidentListHeader query={query} onSort={handleSort} />
              {incidents.length === 0 ? (
                <p style={{ padding: '32px 0', textAlign: 'center', fontSize: 13, color: 'var(--text-muted)' }}>
                  No incidents match these filters.
                </p>
              ) : (
                <div
                  className="stagger-list"
                  style={{ opacity: isFetching ? 0.6 : 1, transition: 'opacity 0.15s' }}
                  aria-busy={isFetching}
                >
                  {incidents.map((incident) => (
                    <IncidentRow
                      key={incident.id}
                      incident={incident}
                      onOpen={() => navigate(`/incidents/${incident.id}/timeline`)}
                      canDelete={canDelete}
                      onDeleteRequest={setDeletingIncident}
                    />
                  ))}
                </div>
              )}
              <div style={{ marginTop: 16 }}>
                <Pagination
                  page={query.page}
                  perPage={query.perPage}
                  total={total}
                  pageSizes={PAGE_SIZES}
                  onPageChange={(page) => updateQuery({ page })}
                  onPerPageChange={(perPage) => updateQuery({ perPage })}
                />
              </div>
            </>
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
