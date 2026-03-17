import { useState } from 'react'
import { useAuditLog, useExportAuditLog } from '@/hooks/useAdmin'
import { PremiumGate } from '@/components/common/PremiumGate'

const HIGH_RISK_ACTIONS = [
  'host.contain',
  'sessions.revoke',
  'incident.delete',
  'user.deactivate',
  'storage.switch',
]

function isHighRisk(action: string) {
  return HIGH_RISK_ACTIONS.some((a) => action.toLowerCase().includes(a.split('.')[0]))
}

export function AuditLogPage() {
  const exportLog = useExportAuditLog()
  const [actionFilter, setActionFilter] = useState('')
  const [fromDate, setFromDate] = useState('')
  const [toDate, setToDate] = useState('')
  const [page, setPage] = useState(1)
  const perPage = 50

  const filters = {
    action: actionFilter || undefined,
    from: fromDate || undefined,
    to: toDate || undefined,
    page,
    per_page: perPage,
  }

  const { data, isLoading } = useAuditLog(filters)
  const entries = data?.data ?? []
  const total = data?.meta?.total ?? 0

  const tableHeaderStyle: React.CSSProperties = {
    padding: '10px 14px',
    fontSize: 11,
    fontWeight: 600,
    color: 'var(--text-muted)',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    textAlign: 'left',
    borderBottom: '1px solid var(--border)',
    background: 'var(--bg-elevated)',
    whiteSpace: 'nowrap',
  }

  const tableCellStyle: React.CSSProperties = {
    padding: '10px 14px',
    fontSize: 12,
    color: 'var(--text-primary)',
    borderBottom: '1px solid var(--border-subtle)',
    verticalAlign: 'middle',
  }

  const inner = (
    <>
      {/* Filter bar */}
      <div
        style={{
          display: 'flex',
          gap: 10,
          alignItems: 'center',
          flexWrap: 'wrap',
          marginBottom: 20,
        }}
      >
        <input
          type="text"
          className="form-input"
          style={{ maxWidth: 220 }}
          placeholder="Filter by action…"
          value={actionFilter}
          onChange={(e) => {
            setActionFilter(e.target.value)
            setPage(1)
          }}
        />
        <input
          type="date"
          className="form-input"
          style={{ maxWidth: 160 }}
          value={fromDate}
          onChange={(e) => {
            setFromDate(e.target.value)
            setPage(1)
          }}
          aria-label="From date"
        />
        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>to</span>
        <input
          type="date"
          className="form-input"
          style={{ maxWidth: 160 }}
          value={toDate}
          onChange={(e) => {
            setToDate(e.target.value)
            setPage(1)
          }}
          aria-label="To date"
        />
        <button
          className="btn btn-ghost btn-sm"
          onClick={() => exportLog({ action: actionFilter || undefined, from: fromDate || undefined, to: toDate || undefined })}
          style={{ marginLeft: 'auto' }}
        >
          Export CSV
        </button>
      </div>

      {/* Table */}
      <div
        style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border)',
          borderRadius: 12,
          overflow: 'hidden',
          marginBottom: 16,
        }}
      >
        {isLoading ? (
          <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
            Loading audit log…
          </div>
        ) : entries.length === 0 ? (
          <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
            No audit log entries found
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th style={tableHeaderStyle}>Timestamp</th>
                  <th style={tableHeaderStyle}>User / Key</th>
                  <th style={tableHeaderStyle}>Action</th>
                  <th style={tableHeaderStyle}>Entity</th>
                  <th style={tableHeaderStyle}>IP Address</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => {
                  const highRisk = isHighRisk(entry.action)
                  return (
                    <tr
                      key={entry.id}
                      style={{
                        background: highRisk ? 'var(--yellow-dim)' : 'transparent',
                      }}
                    >
                      <td
                        style={{
                          ...tableCellStyle,
                          fontFamily: 'JetBrains Mono, monospace',
                          fontSize: 11,
                          whiteSpace: 'nowrap',
                          color: 'var(--text-muted)',
                        }}
                      >
                        {new Date(entry.created_at).toLocaleString()}
                      </td>
                      <td
                        style={{
                          ...tableCellStyle,
                          fontFamily: 'JetBrains Mono, monospace',
                          fontSize: 11,
                          color: 'var(--text-muted)',
                        }}
                      >
                        {entry.user_id
                          ? `user:${entry.user_id.slice(0, 8)}…`
                          : entry.api_key_id
                          ? `key:${entry.api_key_id.slice(0, 8)}…`
                          : '—'}
                      </td>
                      <td style={tableCellStyle}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <span
                            className="chip chip-muted"
                            style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11 }}
                          >
                            {entry.action}
                          </span>
                          {highRisk && (
                            <span
                              className="chip chip-yellow"
                              style={{ fontSize: 10 }}
                              title="High risk action"
                            >
                              ⚠️ HIGH RISK
                            </span>
                          )}
                        </div>
                      </td>
                      <td
                        style={{
                          ...tableCellStyle,
                          color: 'var(--text-muted)',
                          fontSize: 11,
                        }}
                      >
                        {entry.entity_type
                          ? `${entry.entity_type}${entry.entity_id ? `:${entry.entity_id.slice(0, 8)}…` : ''}`
                          : '—'}
                      </td>
                      <td
                        style={{
                          ...tableCellStyle,
                          fontFamily: 'JetBrains Mono, monospace',
                          fontSize: 11,
                          color: 'var(--text-muted)',
                        }}
                      >
                        {entry.ip_address ?? '—'}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination */}
      {total > 0 && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: 12,
            color: 'var(--text-muted)',
          }}
        >
          <span>
            {(page - 1) * perPage + 1}–{Math.min(page * perPage, total)} of {total}
          </span>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              className="btn btn-ghost btn-sm"
              disabled={page === 1}
              onClick={() => setPage((p) => p - 1)}
            >
              ← Prev
            </button>
            <button
              className="btn btn-ghost btn-sm"
              disabled={page * perPage >= total}
              onClick={() => setPage((p) => p + 1)}
            >
              Next →
            </button>
          </div>
        </div>
      )}
    </>
  )

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: 24 }}>
      <h2
        style={{ fontSize: 18, fontWeight: 800, color: 'var(--text-primary)', marginBottom: 24 }}
      >
        📜 Audit Log
      </h2>

      <div style={{ position: 'relative' }}>
        <PremiumGate featureKey="audit_log">{inner}</PremiumGate>
      </div>
    </div>
  )
}
