import { useState, useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useReportTemplates } from '@/hooks/useReportTemplates'
import { useReports, useDeleteReport, useDownloadReport, useGenerateReport } from '@/hooks/useReports'
import { useUIStore } from '@/stores/uiStore'
import { useAiConfig } from '@/hooks/useAiConfig'
import { useIntegrations } from '@/hooks/useIntegrations'
import { Report, FORMAT_LABELS } from '@/types/report'
import { formatRelative } from '@/lib/utils'
import { getSocket } from '@/lib/websocket'

interface Props {
  incidentId: string
  incidentUpdatedAt?: string
}

const STATUS_CHIP: Record<string, string> = {
  pending: 'chip chip-muted',
  generating: 'chip chip-blue',
  ready: 'chip chip-green',
  failed: 'chip chip-red',
}

function AiBanner({ reports }: { reports: Report[] }) {
  const { data: aiConfig } = useAiConfig()
  if (!aiConfig?.is_enabled) return null

  const aiReports = reports.filter((r) => r.is_ai_assisted)
  const isGenerating = aiReports.some((r) => r.status === 'pending' || r.status === 'generating')
  const latestReady = aiReports.find((r) => r.status === 'ready')
  const latestFailed = !isGenerating && !latestReady && aiReports.find((r) => r.status === 'failed')

  let bg = 'rgba(99,102,241,0.06)'
  let border = 'rgba(99,102,241,0.2)'
  let icon = 'robot_color.svg'
  let text: React.ReactNode = null

  if (isGenerating) {
    bg = 'rgba(59,130,246,0.06)'
    border = 'rgba(59,130,246,0.2)'
    icon = '⏳'
    text = <span style={{ color: 'var(--text-secondary)' }}>AI is generating a new report version…</span>
  } else if (latestReady) {
    bg = 'rgba(34,197,94,0.06)'
    border = 'rgba(34,197,94,0.2)'
    icon = '✓'
    text = (
      <span style={{ color: 'var(--text-secondary)' }}>
        AI report is current.{' '}
        <span style={{ color: 'var(--text-muted)' }}>
          Last generated: {formatRelative(latestReady.generated_at ?? latestReady.created_at)} (v{latestReady.version_number})
        </span>
      </span>
    )
  } else if (latestFailed) {
    bg = 'rgba(239,68,68,0.06)'
    border = 'rgba(239,68,68,0.2)'
    icon = '⚠'
    text = <span style={{ color: 'var(--red)' }}>AI report generation failed. It will retry on the next incident update.</span>
  } else {
    text = (
      <span style={{ color: 'var(--text-muted)' }}>
        AI report generation is enabled. Update the incident to trigger the first AI report.
      </span>
    )
  }

  return (
    <div style={{
      background: bg,
      border: `1px solid ${border}`,
      borderRadius: 10,
      padding: '12px 16px',
      marginBottom: 24,
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      fontSize: 13,
    }}>
      {icon.endsWith('.svg')
        ? <img src={`/icons/${icon}`} width={16} height={16} alt="" aria-hidden="true" style={{ flexShrink: 0 }} />
        : <span style={{ fontSize: 16, flexShrink: 0 }}>{icon}</span>
      }
      <div style={{ flex: 1 }}>
        <strong style={{ color: 'var(--text-primary)', fontSize: 12 }}>AI Report Assistant </strong>
        {text}
      </div>
      <span style={{ fontSize: 11, color: 'var(--text-muted)', flexShrink: 0, fontFamily: 'monospace' }}>
        {aiConfig.model_name}
      </span>
    </div>
  )
}

function SharePointBanner({ reports, incidentUpdatedAt }: { reports: Report[], incidentUpdatedAt?: string }) {
  const { data: integrations = [] } = useIntegrations()
  const spEnabled = (integrations as any[]).find((i) => i.name === 'sharepoint')?.is_enabled ?? false
  if (!spEnabled) return null

  const syncedReports = reports.filter((r) => r.sharepoint_url)
  const lastSynced = [...syncedReports].sort(
    (a, b) => new Date(b.generated_at ?? b.created_at).getTime() - new Date(a.generated_at ?? a.created_at).getTime()
  )[0] ?? null

  const hasPendingChanges =
    lastSynced != null &&
    incidentUpdatedAt != null &&
    new Date(incidentUpdatedAt) > new Date(lastSynced.generated_at ?? lastSynced.created_at)

  let bg = 'rgba(14,165,233,0.06)'
  let border = 'rgba(14,165,233,0.2)'
  let icon = 'open_file_folder_color.svg'
  let text: React.ReactNode

  if (!lastSynced) {
    text = (
      <span style={{ color: 'var(--text-muted)' }}>
        SharePoint sync active. Reports will be pushed automatically after each update.
      </span>
    )
  } else if (hasPendingChanges) {
    bg = 'rgba(234,179,8,0.06)'
    border = 'rgba(234,179,8,0.2)'
    icon = '🔄'
    text = (
      <span style={{ color: 'var(--text-secondary)' }}>
        SharePoint sync active.{' '}
        <span style={{ color: 'var(--text-muted)' }}>
          Last synced: {formatRelative(lastSynced.generated_at ?? lastSynced.created_at)} — incident has changes, sync pending.
        </span>
      </span>
    )
  } else {
    bg = 'rgba(34,197,94,0.06)'
    border = 'rgba(34,197,94,0.2)'
    icon = '✓'
    text = (
      <span style={{ color: 'var(--text-secondary)' }}>
        SharePoint sync active.{' '}
        <span style={{ color: 'var(--text-muted)' }}>
          Last synced: {formatRelative(lastSynced.generated_at ?? lastSynced.created_at)} — report is current.
        </span>
      </span>
    )
  }

  return (
    <div style={{
      background: bg,
      border: `1px solid ${border}`,
      borderRadius: 10,
      padding: '12px 16px',
      marginBottom: 24,
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      fontSize: 13,
    }}>
      {icon.endsWith('.svg')
        ? <img src={`/icons/${icon}`} width={16} height={16} alt="" aria-hidden="true" style={{ flexShrink: 0 }} />
        : <span style={{ fontSize: 16, flexShrink: 0 }}>{icon}</span>
      }
      <div style={{ flex: 1 }}>
        <strong style={{ color: 'var(--text-primary)', fontSize: 12 }}>SharePoint Sync </strong>
        {text}
      </div>
    </div>
  )
}

export default function ReportPage({ incidentId, incidentUpdatedAt }: Props) {
  const qc = useQueryClient()
  const addToast = useUIStore((s) => s.addToast)

  const { data: reportTemplates = [], isLoading: loadingTemplates } = useReportTemplates()
  const { data: reports = [], isLoading: loadingReports } = useReports(incidentId)
  const generateReport = useGenerateReport(incidentId)
  const deleteReport = useDeleteReport(incidentId)
  const downloadReport = useDownloadReport()

  const [generatingFor, setGeneratingFor] = useState<string | null>(null)

  // Listen for report:ready and report:sharepoint_synced WebSocket events
  useEffect(() => {
    const socket = getSocket()
    if (!socket) return
    const handler = () => qc.invalidateQueries({ queryKey: ['reports', incidentId] })
    socket.on('report:ready', handler)
    socket.on('report:sharepoint_synced', handler)
    return () => {
      socket.off('report:ready', handler)
      socket.off('report:sharepoint_synced', handler)
    }
  }, [incidentId, qc])

  const handleGenerate = async (templateId: string | null) => {
    const key = templateId ?? '__base__'
    setGeneratingFor(key)
    try {
      await generateReport.mutateAsync({
        format: 'pdf',
        report_template_id: templateId ?? undefined,
        classification: 'confidential',
        include_ai: false,
      })
      addToast('Report generation started', 'success')
    } catch {
      addToast('Failed to start report generation', 'error')
    } finally {
      setGeneratingFor(null)
    }
  }

  const handleDownload = (report: Report) => {
    const filename = `report_${report.id.slice(0, 8)}.pdf`
    downloadReport.mutate({ reportId: report.id, filename })
  }

  // Sort: default first, then alphabetical; exclude hidden templates
  const sortedTemplates = [...reportTemplates]
    .filter((t) => !t.is_hidden)
    .sort((a, b) => {
      if (b.is_default !== a.is_default) return b.is_default ? 1 : -1
      return a.name.localeCompare(b.name)
    })

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '24px 28px' }}>
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: 4 }}>
          Reports
        </h2>
        <p style={{ fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
          Generate PDF incident reports using your report templates.
          Build and manage templates in <strong>Admin → Report Templates</strong>.
        </p>
      </div>

      {/* Report Templates */}
      <section style={{ marginBottom: '36px' }}>
        <h3 style={{
          fontSize: '13px', fontWeight: 700, color: 'var(--text-secondary)',
          textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '14px',
        }}>
          Generate a Report
        </h3>

        {loadingTemplates ? (
          <div style={{ color: 'var(--text-muted)', fontSize: '13px' }}>Loading templates…</div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '12px' }}>
            {/* Base template card — always shown */}
            <div style={{
              background: 'var(--bg-surface)',
              border: '1px solid var(--border)',
              borderRadius: '10px',
              padding: '18px 16px',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px',
            }}>
              <img src="/icons/page_facing_up_color.svg" width={24} height={24} alt="" aria-hidden="true" />
              <div>
                <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
                  Base Template
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                  Built-in scaffold
                </div>
              </div>
              <button
                className="btn btn-accent btn-sm"
                style={{ marginTop: '4px' }}
                disabled={generatingFor === '__base__'}
                onClick={() => handleGenerate(null)}
              >
                {generatingFor === '__base__' ? 'Starting…' : 'Generate PDF'}
              </button>
            </div>

            {/* Custom report templates */}
            {sortedTemplates.map((t) => (
              <div
                key={t.id}
                style={{
                  background: 'var(--bg-surface)',
                  border: `1px solid ${t.is_default ? 'var(--accent)' : 'var(--border)'}`,
                  borderRadius: '10px',
                  padding: '18px 16px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px',
                }}
              >
                {t.logo_data_uri ? (
                  <img
                    src={t.logo_data_uri}
                    alt=""
                    style={{ height: '32px', width: 'auto', objectFit: 'contain', alignSelf: 'flex-start' }}
                  />
                ) : (
                  <img src="/icons/clipboard_color.svg" width={24} height={24} alt="" aria-hidden="true" />
                )}
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                    <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {t.name}
                    </span>
                    {t.is_default && (
                      <span className="chip chip-green" style={{ fontSize: '10px' }}>DEFAULT</span>
                    )}
                  </div>
                  {t.description && (
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                      {t.description}
                    </div>
                  )}
                </div>
                <button
                  className="btn btn-accent btn-sm"
                  style={{ marginTop: '4px' }}
                  disabled={generatingFor === t.id}
                  onClick={() => handleGenerate(t.id)}
                >
                  {generatingFor === t.id ? 'Starting…' : 'Generate PDF'}
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* AI Report Banner */}
      <AiBanner reports={reports} />

      {/* SharePoint Sync Banner */}
      <SharePointBanner reports={reports} incidentUpdatedAt={incidentUpdatedAt} />

      {/* Generated Reports */}
      <section>
        <h3 style={{
          fontSize: '13px', fontWeight: 700, color: 'var(--text-secondary)',
          textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '14px',
        }}>
          Generated Reports
        </h3>

        {loadingReports ? (
          <div style={{ color: 'var(--text-muted)', fontSize: '13px' }}>Loading…</div>
        ) : reports.length === 0 ? (
          <div style={{
            padding: '32px 20px',
            textAlign: 'center',
            border: '1px dashed var(--border)',
            borderRadius: 10,
            color: 'var(--text-muted)',
            fontSize: 13,
          }}>
            No reports generated yet for this incident.
          </div>
        ) : (
          <div style={{ border: '1px solid var(--border)', borderRadius: '8px', overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: 'var(--bg-surface)', borderBottom: '1px solid var(--border)' }}>
                  {['Template', 'Format', 'Version', 'Status', 'Generated', ''].map((h) => (
                    <th
                      key={h}
                      style={{
                        padding: '10px 14px',
                        textAlign: 'left',
                        fontSize: '11px',
                        fontWeight: 700,
                        color: 'var(--text-secondary)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.06em',
                      }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {reports.map((r) => (
                  <tr key={r.id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                    <td style={{ padding: '10px 14px', fontSize: '13px', color: 'var(--text-primary)', fontWeight: 500 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                        {r.report_type}
                        {r.is_ai_assisted && (
                          <span className="chip chip-blue" style={{ fontSize: '10px', padding: '1px 6px' }}>AI</span>
                        )}
                      </div>
                    </td>
                    <td style={{ padding: '10px 14px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                      {FORMAT_LABELS[r.format as keyof typeof FORMAT_LABELS] ?? r.format}
                    </td>
                    <td style={{ padding: '10px 14px', fontSize: '12px', color: 'var(--text-muted)' }}>
                      {r.is_ai_assisted ? `v${r.version_number}` : '—'}
                    </td>
                    <td style={{ padding: '10px 14px' }}>
                      <span className={STATUS_CHIP[r.status] ?? 'chip chip-muted'} style={{ fontSize: '11px' }}>
                        {r.status === 'generating' && <span style={{ marginRight: '4px' }}>⏳</span>}
                        {r.status}
                      </span>
                    </td>
                    <td style={{ padding: '10px 14px', fontSize: '12px', color: 'var(--text-muted)' }}>
                      {r.generated_at ? formatRelative(r.generated_at) : '—'}
                    </td>
                    <td style={{ padding: '10px 14px' }}>
                      <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
                        {r.status === 'ready' && r.sharepoint_url && (
                          <a
                            href={r.sharepoint_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="btn btn-ghost btn-sm"
                          >
                            <img src="/icons/link_color.svg" width={14} height={14} alt="" aria-hidden="true" style={{ verticalAlign: 'middle', marginRight: 4 }} />Access Report
                          </a>
                        )}
                        {r.status === 'ready' && !r.sharepoint_url && (
                          <button
                            className="btn btn-ghost btn-sm"
                            onClick={() => handleDownload(r)}
                            disabled={downloadReport.isPending}
                          >
                            ⬇ Download
                          </button>
                        )}
                        {r.status === 'failed' && r.error_message && (
                          <span
                            style={{ fontSize: '11px', color: 'var(--status-red)', alignSelf: 'center', maxWidth: 240, wordBreak: 'break-word' }}
                            title={r.error_message}
                          >
                            ⚠ {r.error_message.length > 120 ? r.error_message.slice(0, 120) + '…' : r.error_message}
                          </span>
                        )}
                        <button
                          className="btn btn-ghost btn-sm"
                          style={{ color: 'var(--status-red)' }}
                          onClick={() => { if (confirm('Delete this report?')) deleteReport.mutate(r.id) }}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
