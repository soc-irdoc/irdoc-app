import { useState, useEffect } from 'react'
import {
  useBackupConfig,
  useBackupRecords,
  useUpdateBackupConfig,
  useTriggerBackup,
} from '@/hooks/useBackup'
import type { BackupConfig, BackupConfigUpdate } from '@/types/backup'
import apiClient from '@/lib/apiClient'

function SectionCard({
  title,
  children,
}: {
  title: string
  children: React.ReactNode
}) {
  return (
    <div
      style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderRadius: 12,
        overflow: 'hidden',
        marginBottom: 16,
      }}
    >
      <div
        style={{
          padding: '14px 20px',
          borderBottom: '1px solid var(--border)',
          fontSize: 13,
          fontWeight: 700,
          color: 'var(--text-primary)',
        }}
      >
        {title}
      </div>
      <div style={{ padding: 20 }}>{children}</div>
    </div>
  )
}

type RetentionUnit = 'days' | 'months' | 'years'

function retentionFromDays(days: number): { value: number; unit: RetentionUnit } {
  if (days >= 365 && days % 365 === 0) return { value: days / 365, unit: 'years' }
  if (days >= 30 && days % 30 === 0) return { value: days / 30, unit: 'months' }
  return { value: days, unit: 'days' }
}

function retentionToDays(value: number, unit: RetentionUnit): number {
  if (unit === 'years') return value * 365
  if (unit === 'months') return value * 30
  return value
}

function formatRelative(dateStr: string | null): string {
  if (!dateStr) return 'Never'
  const diff = Date.now() - new Date(dateStr).getTime()
  const seconds = Math.floor(diff / 1000)
  if (seconds < 60) return 'Just now'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes} minute${minutes === 1 ? '' : 's'} ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} hour${hours === 1 ? '' : 's'} ago`
  const days = Math.floor(hours / 24)
  return `${days} day${days === 1 ? '' : 's'} ago`
}

function formatBytes(bytes: number | null): string {
  if (bytes === null) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

async function handleDownload(filename: string) {
  try {
    const res = await apiClient.get(`/admin/backup/download/${filename}`, { responseType: 'blob' })
    const url = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    console.error('Download failed:', err)
  }
}

const fieldLabel = (text: string) => (
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
    {text}
  </label>
)

export function BackupsPage() {
  const { data: config } = useBackupConfig()
  const { data: records } = useBackupRecords()
  const updateConfig = useUpdateBackupConfig()
  const triggerBackup = useTriggerBackup()

  const [enabled, setEnabled] = useState(false)
  const [schedule, setSchedule] = useState<BackupConfigUpdate['schedule']>('daily')
  const [retentionValue, setRetentionValue] = useState(30)
  const [retentionUnit, setRetentionUnit] = useState<RetentionUnit>('days')
  const [destination, setDestination] = useState<'local' | 'cloud'>('local')

  useEffect(() => {
    if (!config) return
    setEnabled(config.enabled)
    setSchedule(config.schedule)
    setDestination(config.destination)
    const parsed = retentionFromDays(config.retention_days)
    setRetentionValue(parsed.value)
    setRetentionUnit(parsed.unit)
  }, [config])

  async function handleSave() {
    await updateConfig.mutateAsync({
      enabled,
      schedule,
      retention_days: retentionToDays(retentionValue, retentionUnit),
      destination,
    })
  }

  const isRunning =
    config?.last_backup_status === 'running' || triggerBackup.isPending

  const statusBadge = (status: BackupConfig['last_backup_status']) => {
    if (!status) return <span style={{ color: 'var(--text-muted)' }}>—</span>
    const styles: Record<string, React.CSSProperties> = {
      success: {
        background: 'rgba(34,197,94,0.15)',
        color: 'var(--status-success, #22c55e)',
        border: '1px solid rgba(34,197,94,0.3)',
      },
      failed: {
        background: 'rgba(239,68,68,0.15)',
        color: 'var(--status-error, #ef4444)',
        border: '1px solid rgba(239,68,68,0.3)',
      },
      running: {
        background: 'rgba(59,130,246,0.15)',
        color: 'var(--accent, #3b82f6)',
        border: '1px solid rgba(59,130,246,0.3)',
      },
    }
    const labels = { success: 'Success', failed: 'Failed', running: 'Running' }
    return (
      <span
        style={{
          display: 'inline-block',
          padding: '2px 8px',
          borderRadius: 6,
          fontSize: 12,
          fontWeight: 600,
          ...styles[status],
        }}
      >
        {labels[status]}
      </span>
    )
  }

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: 24 }}>
      <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'Syne, sans-serif', marginBottom: 24 }}>
        Backups
      </div>

      <div style={{ maxWidth: 640 }}>
        {/* Card 1 — Configuration */}
        <SectionCard title="Configuration">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
            {/* Enable toggle */}
            <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={enabled}
                onChange={(e) => setEnabled(e.target.checked)}
                style={{ accentColor: 'var(--accent)', width: 15, height: 15 }}
              />
              <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
                Enable automatic backups
              </span>
            </label>

            {/* Schedule */}
            <div>
              {fieldLabel('Schedule')}
              <select
                className="form-input"
                value={schedule}
                onChange={(e) => setSchedule(e.target.value as BackupConfigUpdate['schedule'])}
              >
                <option value="6h">Every 6 hours</option>
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
              </select>
            </div>

            {/* Retention */}
            <div>
              {fieldLabel('Retention')}
              <div style={{ display: 'flex', gap: 8 }}>
                <input
                  type="number"
                  className="form-input"
                  min={1}
                  value={retentionValue}
                  onChange={(e) => setRetentionValue(Math.max(1, parseInt(e.target.value) || 1))}
                  style={{ width: 80 }}
                />
                <select
                  className="form-input"
                  value={retentionUnit}
                  onChange={(e) => setRetentionUnit(e.target.value as RetentionUnit)}
                  style={{ flex: 1 }}
                >
                  <option value="days">Days</option>
                  <option value="months">Months</option>
                  <option value="years">Years</option>
                </select>
              </div>
            </div>

            {/* Destination */}
            <div>
              {fieldLabel('Destination')}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                  <input
                    type="radio"
                    name="backup_destination"
                    value="local"
                    checked={destination === 'local'}
                    onChange={() => setDestination('local')}
                    style={{ accentColor: 'var(--accent)' }}
                  />
                  <span style={{ fontSize: 13, color: 'var(--text-primary)' }}>Local</span>
                </label>
                <label style={{ display: 'flex', alignItems: 'flex-start', gap: 8, cursor: 'pointer' }}>
                  <input
                    type="radio"
                    name="backup_destination"
                    value="cloud"
                    checked={destination === 'cloud'}
                    onChange={() => setDestination('cloud')}
                    style={{ accentColor: 'var(--accent)', marginTop: 2 }}
                  />
                  <div>
                    <span style={{ fontSize: 13, color: 'var(--text-primary)' }}>Cloud</span>
                    <span style={{ fontSize: 12, color: 'var(--text-muted)', marginLeft: 6 }}>
                      Uses your configured cloud storage
                    </span>
                  </div>
                </label>
              </div>

              {destination === 'cloud' && (
                <div
                  style={{
                    marginTop: 10,
                    padding: '8px 12px',
                    background: 'var(--yellow-dim)',
                    border: '1px solid var(--yellow)',
                    borderRadius: 8,
                    fontSize: 12,
                    color: 'var(--yellow)',
                  }}
                >
                  Make sure cloud storage is configured before enabling cloud backups.
                </div>
              )}
            </div>

            <div>
              <button
                className="btn btn-accent"
                onClick={handleSave}
                disabled={updateConfig.isPending}
              >
                {updateConfig.isPending ? 'Saving…' : 'Save'}
              </button>
            </div>
          </div>
        </SectionCard>

        {/* Card 2 — Backup Status */}
        <SectionCard title="Backup Status">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div>
                <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 4 }}>
                  Last Backup
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-primary)' }}>
                  {formatRelative(config?.last_backup_at ?? null)}
                </div>
              </div>
              <div>
                <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 4 }}>
                  Status
                </div>
                {statusBadge(config?.last_backup_status ?? null)}
              </div>
              <div>
                <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 4 }}>
                  Size
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-primary)' }}>
                  {formatBytes(config?.last_backup_size_bytes ?? null)}
                </div>
              </div>
            </div>

            {config?.last_backup_status === 'failed' && config.last_backup_error && (
              <details
                style={{
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border)',
                  borderRadius: 8,
                  padding: '8px 12px',
                }}
              >
                <summary
                  style={{
                    fontSize: 12,
                    fontWeight: 600,
                    color: 'var(--status-error, #ef4444)',
                    cursor: 'pointer',
                  }}
                >
                  Error details
                </summary>
                <pre
                  style={{
                    marginTop: 8,
                    fontSize: 11,
                    color: 'var(--text-secondary)',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-all',
                    fontFamily: 'monospace',
                  }}
                >
                  {config.last_backup_error}
                </pre>
              </details>
            )}

            <div>
              <button
                className="btn btn-ghost"
                onClick={() => triggerBackup.mutate()}
                disabled={isRunning}
              >
                {isRunning ? 'Running…' : 'Run Now'}
              </button>
            </div>
          </div>
        </SectionCard>

        {/* Card 3 — Backup History */}
        <SectionCard title="Backup History">
          {!records || records.length === 0 ? (
            <div style={{ fontSize: 13, color: 'var(--text-muted)', padding: '8px 0' }}>
              No backups yet.
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr>
                  {['Date', 'Size', 'Destination', 'Status', 'Download'].map((col) => (
                    <th
                      key={col}
                      style={{
                        textAlign: 'left',
                        padding: '6px 8px',
                        borderBottom: '1px solid var(--border)',
                        fontSize: 11,
                        fontWeight: 600,
                        color: 'var(--text-muted)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px',
                      }}
                    >
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {records.map((record) => (
                  <tr key={record.id}>
                    <td style={{ padding: '8px 8px', color: 'var(--text-primary)', borderBottom: '1px solid var(--border)' }}>
                      {new Date(record.created_at).toLocaleString()}
                    </td>
                    <td style={{ padding: '8px 8px', color: 'var(--text-secondary)', borderBottom: '1px solid var(--border)' }}>
                      {formatBytes(record.size_bytes)}
                    </td>
                    <td style={{ padding: '8px 8px', color: 'var(--text-secondary)', borderBottom: '1px solid var(--border)', textTransform: 'capitalize' }}>
                      {record.destination}
                    </td>
                    <td style={{ padding: '8px 8px', borderBottom: '1px solid var(--border)' }}>
                      <span
                        style={{
                          display: 'inline-block',
                          padding: '2px 8px',
                          borderRadius: 6,
                          fontSize: 11,
                          fontWeight: 600,
                          ...(record.status === 'success'
                            ? {
                                background: 'rgba(34,197,94,0.15)',
                                color: 'var(--status-success, #22c55e)',
                                border: '1px solid rgba(34,197,94,0.3)',
                              }
                            : {
                                background: 'rgba(239,68,68,0.15)',
                                color: 'var(--status-error, #ef4444)',
                                border: '1px solid rgba(239,68,68,0.3)',
                              }),
                        }}
                      >
                        {record.status === 'success' ? 'Success' : 'Failed'}
                      </span>
                    </td>
                    <td style={{ padding: '8px 8px', borderBottom: '1px solid var(--border)' }}>
                      {record.status === 'success' && record.destination === 'local' ? (
                        <button
                          className="btn btn-ghost"
                          style={{ fontSize: 11, padding: '3px 10px' }}
                          onClick={() => handleDownload(record.filename)}
                        >
                          Download
                        </button>
                      ) : record.status === 'success' ? (
                        <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>Cloud</span>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          <p
            style={{
              marginTop: 14,
              fontSize: 11,
              color: 'var(--text-muted)',
              lineHeight: 1.5,
            }}
          >
            Backups are AES-256-GCM encrypted. Keep your .env — you need SECRET_KEY to decrypt them.
          </p>
        </SectionCard>
      </div>
    </div>
  )
}
