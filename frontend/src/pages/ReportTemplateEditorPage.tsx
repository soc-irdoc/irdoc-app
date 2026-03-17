/**
 * /report-templates/:id and /report-templates/new
 *
 * Full-page template builder. Wraps ReportTemplateBuilder with
 * name/destination editing + save/preview actions.
 */
import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import ReportTemplateBuilder from '@/components/reports/ReportTemplateBuilder'
import { Modal } from '@/components/common/Modal'
import {
  useReportTemplate,
  useUpdateReportTemplate,
} from '@/hooks/useReportTemplates'
import { ReportBlock, DESTINATION_OPTIONS } from '@/types/report'

let _id = 1
function tempId() { return `blk-${Date.now()}-${_id++}` }

function hydrateBlocks(schemaJson: Omit<ReportBlock, 'id'>[]): ReportBlock[] {
  return (schemaJson ?? []).map((b) => ({ ...b, id: tempId() }))
}

function stripIds(blocks: ReportBlock[]): Omit<ReportBlock, 'id'>[] {
  return blocks.map(({ id: _id, ...rest }) => rest)
}

export default function ReportTemplateEditorPage() {
  const { id: templateId } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const isNew = templateId === 'new'
  const { data: remote, isLoading } = useReportTemplate(isNew ? null : templateId ?? null)
  const updateTemplate = useUpdateReportTemplate(templateId ?? '')

  const [name, setName] = useState('')
  const [destination, setDestination] = useState('custom')
  const [blocks, setBlocks] = useState<ReportBlock[]>([])
  const [dirty, setDirty] = useState(false)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  // Load remote template into local state
  useEffect(() => {
    if (remote) {
      setName(remote.name)
      setDestination(remote.destination)
      setBlocks(hydrateBlocks(remote.schema_json))
      setDirty(false)
    }
  }, [remote])

  const handleBlocksChange = (newBlocks: ReportBlock[]) => {
    setBlocks(newBlocks)
    setDirty(true)
  }

  const handleSave = async () => {
    if (isNew) return  // new templates are created via the list page first
    setSaving(true)
    try {
      await updateTemplate.mutateAsync({
        name,
        destination,
        schema_json: stripIds(blocks),
      })
      setDirty(false)
    } finally {
      setSaving(false)
    }
  }

  if (!isNew && isLoading) {
    return (
      <div style={{ padding: '40px', color: 'var(--text-muted)', fontSize: '13px' }}>
        Loading template…
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: 'var(--bg-base)' }}>
      {/* Top bar */}
      <div
        style={{
          height: '56px',
          background: 'var(--bg-surface)',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          padding: '0 20px',
          gap: '14px',
          flexShrink: 0,
        }}
      >
        <button className="btn btn-ghost btn-sm" onClick={() => navigate('/report-templates')}>
          ← Templates
        </button>

        <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: '12px' }}>
          <input
            className="form-input"
            style={{ width: '260px', fontSize: '14px', fontWeight: 600 }}
            value={name}
            onChange={(e) => { setName(e.target.value); setDirty(true) }}
            placeholder="Template name"
          />
          <div className="select-wrap">
            <select
              className="form-input"
              style={{ width: '160px', fontSize: '13px' }}
              value={destination}
              onChange={(e) => { setDestination(e.target.value); setDirty(true) }}
            >
              {DESTINATION_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          {dirty && (
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
              Unsaved changes
            </span>
          )}
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            {blocks.length} block{blocks.length !== 1 ? 's' : ''}
          </div>
          <button
            className="btn btn-accent btn-sm"
            onClick={handleSave}
            disabled={saving || isNew || !dirty}
          >
            {saving ? 'Saving…' : 'Save Template'}
          </button>
        </div>
      </div>

      {/* Builder */}
      <div style={{ flex: 1, overflow: 'hidden' }}>
        <ReportTemplateBuilder
          blocks={blocks}
          onChange={handleBlocksChange}
        />
      </div>

      {/* Preview modal (iframe) */}
      {previewUrl && (
        <Modal title="Report Preview" onClose={() => setPreviewUrl(null)} size="lg">
          <iframe
            src={previewUrl}
            style={{ width: '100%', height: '70vh', border: 'none', borderRadius: '4px' }}
            title="Report preview"
          />
        </Modal>
      )}
    </div>
  )
}
