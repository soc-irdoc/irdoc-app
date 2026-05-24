import { useState } from 'react'
import { Modal } from '@/components/common/Modal'
import { useGenerateReport } from '@/hooks/useReports'
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

const FORMATS: ReportFormat[] = ['markdown', 'html', 'pdf', 'docx']

export default function GenerateReportModal({ incidentId, template, onClose }: Props) {
  const [format, setFormat] = useState<ReportFormat>('markdown')
  const [classification, setClassification] = useState('confidential')
  const [includeAi, setIncludeAi] = useState(false)

  const generate = useGenerateReport(incidentId)

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
            {FORMATS.map((f) => (
              <button
                key={f}
                className={`btn ${format === f ? 'btn-accent' : 'btn-ghost'} btn-sm`}
                onClick={() => setFormat(f)}
              >
                {FORMAT_LABELS[f]}
              </button>
            ))}
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
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontWeight: 600, fontSize: '13px' }}>Include AI Narrative</div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
              AI-generated executive summary &amp; recommendations
            </div>
          </div>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={includeAi}
              onChange={(e) => setIncludeAi(e.target.checked)}
              style={{ width: '16px', height: '16px' }}
            />
          </label>
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
