import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { useReportTemplates, useCloneReportTemplate } from '@/hooks/useReportTemplates'
import { useReports, useDeleteReport, useDownloadReport } from '@/hooks/useReports'
import PremiumGate from '@/components/common/PremiumGate'
import GenerateReportModal from './GenerateReportModal'
import SyncPolicySection from './SyncPolicySection'
import { useFeatureFlags } from '@/hooks/useFeatureFlags'
import { ReportTemplate, Report, FORMAT_LABELS } from '@/types/report'
import { formatRelative } from '@/lib/utils'
import { getSocket } from '@/lib/websocket'
import { useEffect } from 'react'

interface Props {
  incidentId: string
}

const TEMPLATE_ICONS: Record<string, string> = {
  management: '📊',
  analyst: '🔬',
  legal: '⚖️',
  custom: '✏️',
}

const STATUS_CHIP: Record<string, string> = {
  pending: 'chip chip-muted',
  generating: 'chip chip-blue',
  ready: 'chip chip-green',
  failed: 'chip chip-red',
}

export default function ReportPage({ incidentId }: Props) {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { hasFeature } = useFeatureFlags()
  const { data: templates = [], isLoading: loadingTemplates } = useReportTemplates()
  const { data: reports = [], isLoading: loadingReports } = useReports(incidentId)
  const cloneTemplate = useCloneReportTemplate()
  const deleteReport = useDeleteReport(incidentId)
  const downloadReport = useDownloadReport()

  const [generateFor, setGenerateFor] = useState<ReportTemplate | null>(null)

  // Listen for report:ready WebSocket event
  useEffect(() => {
    const socket = getSocket()
    if (!socket) return
    const handler = () => qc.invalidateQueries({ queryKey: ['reports', incidentId] })
    socket.on('report:ready', handler)
    return () => { socket.off('report:ready', handler) }
  }, [incidentId, qc])

  const handleDownload = (report: Report) => {
    const ext: Record<string, string> = { pdf: 'pdf', docx: 'docx', markdown: 'md', html: 'html' }
    const filename = `${report.report_type.replace(/\s/g, '_')}_${report.id.slice(0, 8)}.${ext[report.format] ?? 'bin'}`
    downloadReport.mutate({ reportId: report.id, filename })
  }

  return (
    <div style={{ padding: '24px 28px', maxWidth: '960px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h2 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text-primary)' }}>Reports</h2>
        <PremiumGate featureKey="report_template_builder">
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => navigate('/report-templates')}
          >
            Manage Templates
          </button>
        </PremiumGate>
      </div>

      {/* Generate a Report */}
      <section style={{ marginBottom: '36px' }}>
        <h3 style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '14px' }}>
          Generate a Report
        </h3>

        {loadingTemplates ? (
          <div style={{ color: 'var(--text-muted)', fontSize: '13px' }}>Loading templates…</div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(170px, 1fr))', gap: '12px' }}>
            {templates.map((t) => (
              <div
                key={t.id}
                style={{
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border)',
                  borderRadius: '10px',
                  padding: '18px 16px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px',
                }}
              >
                <div style={{ fontSize: '24px' }}>{TEMPLATE_ICONS[t.destination] ?? '📋'}</div>
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>{t.name}</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px', textTransform: 'capitalize' }}>
                    {t.destination}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '6px', marginTop: '4px', flexWrap: 'wrap' }}>
                  <button
                    className="btn btn-accent btn-sm"
                    style={{ flex: 1 }}
                    onClick={() => setGenerateFor(t)}
                  >
                    Generate
                  </button>
                  {t.is_system ? (
                    <button
                      className="btn btn-ghost btn-sm"
                      onClick={() => cloneTemplate.mutate(t.id)}
                      disabled={cloneTemplate.isPending}
                      title="Clone to create editable copy"
                    >
                      Clone
                    </button>
                  ) : (
                    <PremiumGate featureKey="report_template_builder">
                      <button
                        className="btn btn-ghost btn-sm"
                        onClick={() => navigate(`/report-templates/${t.id}`)}
                      >
                        Edit
                      </button>
                    </PremiumGate>
                  )}
                </div>
              </div>
            ))}

            {/* New Template card */}
            <PremiumGate featureKey="report_template_builder">
              <button
                style={{
                  background: 'transparent',
                  border: '1px dashed var(--border)',
                  borderRadius: '10px',
                  padding: '18px 16px',
                  cursor: 'pointer',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                  color: 'var(--text-muted)',
                  fontSize: '13px',
                  width: '100%',
                }}
                onClick={() => navigate('/report-templates/new')}
              >
                <span style={{ fontSize: '24px' }}>+</span>
                <span>New Template</span>
              </button>
            </PremiumGate>
          </div>
        )}
      </section>

      {/* Sync Policies */}
      <section style={{ marginBottom: '36px' }}>
        <SyncPolicySection incidentId={incidentId} />
      </section>

      {/* Generated Reports */}
      <section>
        <h3 style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '14px' }}>
          Generated Reports
        </h3>

        {loadingReports ? (
          <div style={{ color: 'var(--text-muted)', fontSize: '13px' }}>Loading…</div>
        ) : reports.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', fontSize: '13px', fontStyle: 'italic' }}>
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
                  <tr
                    key={r.id}
                    style={{ borderBottom: '1px solid var(--border-subtle)' }}
                  >
                    <td style={{ padding: '10px 14px', fontSize: '13px', color: 'var(--text-primary)', fontWeight: 500 }}>
                      {r.report_type}
                      {r.is_ai_assisted && (
                        <span className="chip chip-purple" style={{ marginLeft: '6px', fontSize: '10px' }}>AI</span>
                      )}
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
                            title={r.error_message}
                            style={{ fontSize: '11px', color: 'var(--status-red)', cursor: 'help', alignSelf: 'center' }}
                          >
                            ⚠ Error
                          </span>
                        )}
                        <button
                          className="btn btn-ghost btn-sm"
                          style={{ color: 'var(--status-red)' }}
                          onClick={() => {
                            if (confirm('Delete this report?')) deleteReport.mutate(r.id)
                          }}
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

      {/* Generate Modal */}
      {generateFor && (
        <GenerateReportModal
          incidentId={incidentId}
          template={generateFor}
          onClose={() => setGenerateFor(null)}
        />
      )}
    </div>
  )
}
