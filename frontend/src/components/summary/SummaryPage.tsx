import { useState } from 'react'
import { useIncident, useUpdateIncident, useIncidentStats } from '@/hooks/useIncident'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { Button } from '@/components/common/Button'
import { useUIStore } from '@/stores/uiStore'
import { SEVERITY_LABELS, STATUS_LABELS } from '@/types/incident'
import { formatDateTime, formatRelative } from '@/lib/utils'

interface SummaryPageProps {
  incidentId: string
}

function StatCard({
  title,
  value,
  color,
}: {
  title: string
  value: string | number
  color?: string
}) {
  return (
    <div
      style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderRadius: 12,
        padding: 18,
      }}
    >
      <h3
        style={{
          fontSize: 12,
          color: 'var(--text-muted)',
          textTransform: 'uppercase',
          letterSpacing: '0.5px',
          marginBottom: 8,
        }}
      >
        {title}
      </h3>
      <p
        style={{
          fontSize: 28,
          fontWeight: 800,
          color: color ?? 'var(--text-primary)',
        }}
      >
        {value}
      </p>
    </div>
  )
}

export function SummaryPage({ incidentId }: SummaryPageProps) {
  const addToast = useUIStore((s) => s.addToast)
  const { data: incident, isLoading } = useIncident(incidentId)
  const { data: stats } = useIncidentStats(incidentId)
  const updateIncident = useUpdateIncident(incidentId)

  const [editing, setEditing] = useState(false)
  const [summary, setSummary] = useState('')

  function startEdit() {
    setSummary(incident?.executive_summary ?? '')
    setEditing(true)
  }

  async function saveSummary() {
    try {
      await updateIncident.mutateAsync({ executive_summary: summary })
      setEditing(false)
      addToast('Summary saved', 'success')
    } catch {
      addToast('Failed to save summary', 'error')
    }
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <LoadingSpinner />
      </div>
    )
  }
  if (!incident) return null

  const taskPct =
    (stats?.task_total ?? 0) > 0
      ? Math.round(((stats?.task_done ?? 0) / (stats?.task_total ?? 1)) * 100)
      : 0

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: 24 }}>
      <h2
        style={{
          fontSize: 18,
          fontWeight: 800,
          marginBottom: 20,
          color: 'var(--text-primary)',
          display: 'flex',
          alignItems: 'center',
          gap: 10,
        }}
      >
        📊 Incident Summary
      </h2>

      {/* Stat cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
          gap: 16,
          marginBottom: 20,
        }}
      >
        <StatCard title="Severity" value={SEVERITY_LABELS[incident.severity]} color="var(--red)" />
        <StatCard title="Status" value={STATUS_LABELS[incident.status]} color="var(--accent)" />
        <StatCard title="Timeline" value={stats?.timeline_count ?? '—'} color="var(--blue)" />
        <StatCard title="IOCs" value={stats?.ioc_count ?? '—'} color="var(--red)" />
        <StatCard
          title="Tasks"
          value={`${taskPct}%`}
          color={taskPct === 100 ? 'var(--green)' : 'var(--yellow)'}
        />
        <StatCard title="Affected Users" value={incident.affected_users} color="var(--purple)" />
      </div>

      {/* Incident details */}
      <div
        style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border)',
          borderRadius: 12,
          padding: 20,
          marginBottom: 16,
        }}
      >
        <h3
          style={{
            fontSize: 13,
            fontWeight: 700,
            marginBottom: 12,
            color: 'var(--text-primary)',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}
        >
          📋 Incident Details
        </h3>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <tbody>
            {[
              ['Reference', incident.incident_ref],
              ['Created', formatDateTime(incident.created_at)],
              ['Last Updated', formatRelative(incident.updated_at)],
              ...(incident.contained_at
                ? [['Contained', formatDateTime(incident.contained_at)]]
                : []),
              ...(incident.closed_at
                ? [['Closed', formatDateTime(incident.closed_at)]]
                : []),
              ...(incident.attack_vector.length > 0
                ? [['Attack Vector', incident.attack_vector.join(', ')]]
                : []),
            ].map(([label, value]) => (
              <tr key={label}>
                <td
                  style={{
                    padding: '8px 12px 8px 0',
                    color: 'var(--text-muted)',
                    fontWeight: 600,
                    width: 160,
                    verticalAlign: 'top',
                  }}
                >
                  {label}
                </td>
                <td
                  style={{
                    padding: '8px 0',
                    color: 'var(--text-primary)',
                    fontFamily: 'JetBrains Mono, monospace',
                  }}
                >
                  {value}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Executive Summary */}
      <div
        style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border)',
          borderRadius: 12,
          padding: 20,
          marginBottom: 16,
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: 12,
          }}
        >
          <h3 style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>
            📝 Executive Summary
          </h3>
          {!editing && (
            <Button variant="ghost" size="sm" onClick={startEdit}>
              Edit
            </Button>
          )}
        </div>

        {editing ? (
          <div>
            <textarea
              className="form-input"
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              rows={8}
              placeholder="Write an executive summary of this incident..."
              style={{ fontFamily: 'Syne, sans-serif', lineHeight: 1.6 }}
            />
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 12 }}>
              <Button variant="ghost" size="sm" onClick={() => setEditing(false)}>Cancel</Button>
              <Button
                variant="accent"
                size="sm"
                loading={updateIncident.isPending}
                onClick={saveSummary}
              >
                Save
              </Button>
            </div>
          </div>
        ) : (
          <p
            style={{
              fontSize: 13,
              lineHeight: 1.7,
              color: incident.executive_summary
                ? 'var(--text-primary)'
                : 'var(--text-muted)',
              whiteSpace: 'pre-wrap',
              fontFamily: 'JetBrains Mono, monospace',
            }}
          >
            {incident.executive_summary || 'No executive summary yet. Click Edit to add one.'}
          </p>
        )}
      </div>
    </div>
  )
}
