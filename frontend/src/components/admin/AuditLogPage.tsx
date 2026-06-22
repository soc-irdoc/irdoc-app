import React, { useState } from 'react'
import { useAuditLog, useExportAuditLog } from '@/hooks/useAdmin'

const HIGH_RISK_ACTIONS = [
  'crowdstrike.contain_host',
  'azuread.revoke_sessions',
  'azuread.reset_password',
  'incident.deleted',
  'user.deactivated',
  'storage.backend_switched',
  'api_key.revoked',
]

const ACTION_LABELS: Record<string, string> = {
  'incident.created': 'Incident Created',
  'incident.status_changed': 'Status Changed',
  'incident.severity_changed': 'Severity Changed',
  'incident.assignee_changed': 'Assignee Changed',
  'incident.deleted': 'Incident Deleted',
  'incident.comment_added': 'Comment Added',
  'user.login': 'User Login',
  'user.logout': 'User Logout',
  'user.created': 'User Created',
  'user.invited': 'User Invited',
  'user.role_changed': 'Role Changed',
  'user.deactivated': 'User Deactivated',
  'user.reactivated': 'User Reactivated',
  'api_key.created': 'API Key Created',
  'api_key.revoked': 'API Key Revoked',
  'org.settings_updated': 'Settings Updated',
  'storage.config_updated': 'Storage Config Updated',
  'storage.backend_switched': 'Storage Backend Switched',
  'sso.config_updated': 'SSO Config Updated',
  'integration.config_saved': 'Integration Configured',
  'integration.enabled': 'Integration Enabled',
  'integration.disabled': 'Integration Disabled',
  'integration.tested': 'Connection Tested',
  'crowdstrike.contain_host': 'Host Contained',
  'azuread.revoke_sessions': 'Sessions Revoked',
  'azuread.reset_password': 'Password Reset',
}

const CATEGORIES = [
  { key: undefined as string | undefined, label: 'All' },
  { key: 'incidents', label: 'Incidents' },
  { key: 'users', label: 'Users' },
  { key: 'auth', label: 'Auth' },
  { key: 'settings', label: 'Settings' },
  { key: 'integrations', label: 'Integrations' },
  { key: 'api_keys', label: 'API Keys' },
  { key: 'high_risk', label: '⚠ High Risk' },
] as const

function isHighRisk(action: string) {
  return HIGH_RISK_ACTIONS.includes(action)
}

function renderDiff(diff: Record<string, unknown> | null | undefined): React.ReactNode {
  if (!diff) return null
  const visibleEntries = Object.entries(diff).filter(([k]) => !k.startsWith('_'))
  if (visibleEntries.length === 0) return null
  const hasFromTo = 'from' in diff && 'to' in diff
  return (
    <dl style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '2px 16px', fontSize: 11, color: 'var(--text-primary)' }}>
      {hasFromTo && (
        <>
          <dt style={{ color: 'var(--text-muted)' }}>Changed</dt>
          <dd>{String(diff.from ?? '—')} → {String(diff.to ?? '—')}</dd>
        </>
      )}
      {visibleEntries.filter(([k]) => k !== 'from' && k !== 'to').map(([key, val]) => (
        <React.Fragment key={key}>
          <dt style={{ color: 'var(--text-muted)', textTransform: 'capitalize' }}>{key.replace(/_/g, ' ')}</dt>
          <dd>{String(val)}</dd>
        </React.Fragment>
      ))}
    </dl>
  )
}

export function AuditLogPage() {
  const exportLog = useExportAuditLog()
  const [actionFilter, setActionFilter] = useState('')
  const [fromDate, setFromDate] = useState('')
  const [toDate, setToDate] = useState('')
  const [page, setPage] = useState(1)
  const [category, setCategory] = useState<string | undefined>(undefined)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const perPage = 50

  const filters = {
    action: actionFilter || undefined,
    category,
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
      {/* Category pills */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
        {CATEGORIES.map((cat) => (
          <button
            key={String(cat.key ?? 'all')}
            onClick={() => { setCategory(cat.key); setPage(1) }}
            className={category === cat.key ? 'btn btn-primary btn-sm' : 'btn btn-ghost btn-sm'}
          >
            {cat.label}
          </button>
        ))}
      </div>

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
                {entries.map((item) => {
                  const highRisk = isHighRisk(item.action)
                  return (
                    <React.Fragment key={item.id}>
                      <tr
                        style={{
                          background: highRisk ? 'var(--yellow-dim)' : 'transparent',
                          cursor: 'pointer',
                        }}
                        onClick={() => setExpandedId(expandedId === item.id ? null : item.id)}
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
                          {new Date(item.created_at).toLocaleString()}
                        </td>
                        <td
                          style={{
                            ...tableCellStyle,
                            fontFamily: 'JetBrains Mono, monospace',
                            fontSize: 11,
                            color: 'var(--text-muted)',
                          }}
                        >
                          {item.actor_label ?? (item.user_id
                            ? `user:${String(item.user_id).slice(0, 8)}…`
                            : item.api_key_id
                            ? `key:${String(item.api_key_id).slice(0, 8)}…`
                            : '—'
                          )}
                        </td>
                        <td style={tableCellStyle}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            <span
                              className="chip chip-muted"
                              style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11 }}
                            >
                              {ACTION_LABELS[item.action] ?? item.action}
                            </span>
                            {highRisk && (
                              <span
                                className="chip chip-yellow"
                                style={{ fontSize: 10 }}
                                title="High risk action"
                              >
                                <img src="/icons/warning_color.svg" width={14} height={14} alt="" aria-hidden="true" style={{ verticalAlign: 'middle', marginRight: 3 }} />HIGH RISK
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
                          {item.entity_label ?? (item.entity_type && item.entity_id
                            ? `${item.entity_type}:${String(item.entity_id).slice(0, 8)}…`
                            : '—'
                          )}
                        </td>
                        <td
                          style={{
                            ...tableCellStyle,
                            fontFamily: 'JetBrains Mono, monospace',
                            fontSize: 11,
                            color: 'var(--text-muted)',
                          }}
                        >
                          {item.ip_address ?? '—'}
                        </td>
                      </tr>
                      {expandedId === item.id && (
                        <tr>
                          <td
                            colSpan={5}
                            style={{
                              padding: '10px 14px',
                              background: 'var(--bg-elevated)',
                              borderBottom: '1px solid var(--border)',
                            }}
                          >
                            {renderDiff(item.diff)}
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
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
      <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'Syne, sans-serif', marginBottom: 24 }}>
        Audit Log
      </div>

      <div>{inner}</div>
    </div>
  )
}
