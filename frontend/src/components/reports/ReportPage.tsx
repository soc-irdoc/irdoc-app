import { useState, useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useReportTemplates } from '@/hooks/useReportTemplates'
import { useReports, useDeleteReport, useDownloadReport, useGenerateReport } from '@/hooks/useReports'
import { useUIStore } from '@/stores/uiStore'
import { Report, FORMAT_LABELS } from '@/types/report'
import { formatRelative } from '@/lib/utils'
import { getSocket } from '@/lib/websocket'

interface Props {
  incidentId: string
}

const STATUS_CHIP: Record<string, string> = {
  pending: 'chip chip-muted',
  generating: 'chip chip-blue',
  ready: 'chip chip-green',
  failed: 'chip chip-red',
}

export default function ReportPage({ incidentId }: Props) {
  const qc = useQueryClient()
  const addToast = useUIStore((s) => s.addToast)

  const { data: reportTemplates = [], isLoading: loadingTemplates } = useReportTemplates()
  const { data: reports = [], isLoading: loadingReports } = useReports(incidentId)
  const generateReport = useGenerateReport(incidentId)
  const deleteReport = useDeleteReport(incidentId)
  const downloadReport = useDownloadReport()

  const [generatingFor, setGeneratingFor] = useState<string | null>(null)

  // Listen for report:ready WebSocket event
  useEffect(() => {
    const socket = getSocket()
    if (!socket) return
    const handler = () => qc.invalidateQueries({ queryKey: ['reports', incidentId] })
    socket.on('report:ready', handler)
    return () => { socket.off('report:ready', handler) }
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

  // Sort: default first, then alphabetical
  const sortedTemplates = [...reportTemplates].sort((a, b) => {
    if (b.is_default !== a.is_default) return b.is_default ? 1 : -1
    return a.name.localeCompare(b.name)
  })

  return (
    <div style={{ padding: '24px 28px', maxWidth: '960px' }}>
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
              <div style={{ fontSize: '24px' }}>📄</div>
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
                  <div style={{ fontSize: '24px' }}>📋</div>
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
                  {['Template', 'Format', 'Status', 'Generated', ''].map((h) => (
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
                      {r.report_type}
                    </td>
                    <td style={{ padding: '10px 14px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                      {FORMAT_LABELS[r.format as keyof typeof FORMAT_LABELS] ?? r.format}
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
                        {r.status === 'ready' && (
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
