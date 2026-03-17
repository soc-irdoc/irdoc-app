import { useState } from 'react'
import { Modal } from '@/components/common/Modal'
import PremiumGate from '@/components/common/PremiumGate'
import { useGenerateReport } from '@/hooks/useReports'
import { useFeatureFlags } from '@/hooks/useFeatureFlags'
import {
  ReportTemplate,
  ReportFormat,
  FORMAT_LABELS,
  CLASSIFICATION_OPTIONS,
} from '@/types/report'

interface Props {
  incidentId: string
  template: ReportTemplate
  onClose: () => void
}

const FORMATS: { value: ReportFormat; premium: boolean }[] = [
  { value: 'markdown', premium: false },
  { value: 'html', premium: false },
  { value: 'pdf', premium: true },
  { value: 'docx', premium: true },
]

export default function GenerateReportModal({ incidentId, template, onClose }: Props) {
  const { hasFeature } = useFeatureFlags()
  const [format, setFormat] = useState<ReportFormat>('markdown')
  const [classification, setClassification] = useState('confidential')
  const [includeAi, setIncludeAi] = useState(false)

  const generate = useGenerateReport(incidentId)

  const hasPdfExport = hasFeature('report_pdf_export')
  const hasDocxExport = hasFeature('report_docx_export')
  const hasAi = hasFeature('ai_summaries')

  const formatEnabled = (f: ReportFormat) => {
    if (f === 'pdf') return hasPdfExport
    if (f === 'docx') return hasDocxExport
    return true
  }

  const handleGenerate = async () => {
    await generate.mutateAsync({
      report_template_id: template.id,
      format,
      classification,
      include_ai: includeAi,
    })
    onClose()
  }

  return (
    <Modal title={`Generate: ${template.name}`} onClose={onClose} size="sm">
      <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
        {/* Format */}
        <div>
          <label className="form-label" style={{ display: 'block', marginBottom: '8px' }}>
            Format
          </label>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {FORMATS.map(({ value: f, premium }) => {
              const enabled = formatEnabled(f)
              const selected = format === f
              return (
                <div key={f} style={{ position: 'relative' }}>
                  {premium && !enabled ? (
                    <PremiumGate featureKey={f === 'pdf' ? 'report_pdf_export' : 'report_docx_export'}>
                      <button
                        className={`btn ${selected ? 'btn-accent' : 'btn-ghost'} btn-sm`}
                        disabled
                      >
                        {FORMAT_LABELS[f]}
                      </button>
                    </PremiumGate>
                  ) : (
                    <button
                      className={`btn ${selected ? 'btn-accent' : 'btn-ghost'} btn-sm`}
                      onClick={() => setFormat(f)}
                    >
                      {FORMAT_LABELS[f]}
                    </button>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* Classification */}
        <div>
          <label className="form-label" style={{ display: 'block', marginBottom: '6px' }}>
            Classification
          </label>
          <div className="select-wrap">
            <select
              className="form-input"
              value={classification}
              onChange={(e) => setClassification(e.target.value)}
            >
              {CLASSIFICATION_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
        </div>

        {/* AI toggle */}
        <div>
          <PremiumGate featureKey="ai_summaries">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontWeight: 600, fontSize: '13px' }}>Include AI Narrative</div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                  AI-generated executive summary &amp; recommendations
                </div>
              </div>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: hasAi ? 'pointer' : 'not-allowed' }}>
                <input
                  type="checkbox"
                  checked={includeAi}
                  onChange={(e) => setIncludeAi(e.target.checked)}
                  disabled={!hasAi}
                  style={{ width: '16px', height: '16px' }}
                />
              </label>
            </div>
          </PremiumGate>
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', paddingTop: '4px' }}>
          <button className="btn btn-ghost" onClick={onClose} disabled={generate.isPending}>
            Cancel
          </button>
          <button
            className="btn btn-accent"
            onClick={handleGenerate}
            disabled={generate.isPending}
          >
            {generate.isPending ? (
              <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className="spinner" style={{ width: '14px', height: '14px', border: '2px solid rgba(255,255,255,.3)', borderTopColor: 'white', borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} />
                Generating…
              </span>
            ) : (
              'Generate Report'
            )}
          </button>
        </div>
      </div>
    </Modal>
  )
}
