/**
 * /report-templates/:id and /report-templates/new
 *
 * Full-page template builder. Wraps ReportTemplateBuilder with
 * name/destination editing + save/preview actions.
 */
import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import ReportTemplateBuilder from '@/components/reports/ReportTemplateBuilder'
import { Modal } from '@/components/common/Modal'
import {
  useReportTemplate,
  useCreateReportTemplate,
  useUpdateReportTemplate,
  useUploadTemplateLogo,
} from '@/hooks/useReportTemplates'
import { ReportBlock, DESTINATION_OPTIONS } from '@/types/report'
import { AppShell } from '@/components/layout/AppShell'

let _id = 1
function tempId() { return `blk-${Date.now()}-${_id++}` }

function hydrateBlocks(schemaJson: Omit<ReportBlock, 'id'>[]): ReportBlock[] {
  return (schemaJson ?? []).map((b) => ({ ...b, id: tempId() }))
}

function stripIds(blocks: ReportBlock[]): Omit<ReportBlock, 'id'>[] {
  return blocks.map(({ id, ...rest }) => rest)
}

export default function ReportTemplateEditorPage() {
  const { id: templateId } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const isNew = templateId === 'new'
  const { data: remote, isLoading } = useReportTemplate(isNew ? null : templateId ?? null)
  const createTemplate = useCreateReportTemplate()
  const updateTemplate = useUpdateReportTemplate(templateId ?? '')
  const uploadLogo = useUploadTemplateLogo(templateId ?? '')

  const [name, setName] = useState('')
  const [destination, setDestination] = useState('custom')
  const [blocks, setBlocks] = useState<ReportBlock[]>([])
  const [dirty, setDirty] = useState(false)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  // Brand settings (only meaningful for existing templates)
  const [primaryColour, setPrimaryColour] = useState('#F97316')
  const [companyName, setCompanyName] = useState('')
  const [logoPreview, setLogoPreview] = useState<string | null>(null)
  const logoInputRef = useRef<HTMLInputElement>(null)
  const brandDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Load remote template into local state
  useEffect(() => {
    if (remote) {
      setName(remote.name)
      setDestination(remote.destination)
      setBlocks(hydrateBlocks(remote.schema_json))
      setPrimaryColour(remote.primary_colour ?? '#F97316')
      setCompanyName(remote.company_name ?? '')
      setLogoPreview(remote.logo_data_uri ?? null)
      setDirty(false)
    }
  }, [remote])

  const handleBrandColourChange = useCallback((colour: string) => {
    setPrimaryColour(colour)
    if (!templateId || isNew) return
    if (brandDebounceRef.current) clearTimeout(brandDebounceRef.current)
    brandDebounceRef.current = setTimeout(() => {
      updateTemplate.mutate({ primary_colour: colour })
    }, 600)
  }, [templateId, isNew, updateTemplate])

  const handleCompanyNameChange = useCallback((value: string) => {
    setCompanyName(value)
    if (!templateId || isNew) return
    if (brandDebounceRef.current) clearTimeout(brandDebounceRef.current)
    brandDebounceRef.current = setTimeout(() => {
      updateTemplate.mutate({ company_name: value })
    }, 800)
  }, [templateId, isNew, updateTemplate])

  const handleLogoChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || isNew) return
    await uploadLogo.mutateAsync(file)
    const reader = new FileReader()
    reader.onload = () => setLogoPreview(reader.result as string)
    reader.readAsDataURL(file)
  }

  const handleBlocksChange = (newBlocks: ReportBlock[]) => {
    setBlocks(newBlocks)
    setDirty(true)
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      if (isNew) {
        const created = await createTemplate.mutateAsync({
          name,
          destination,
          schema_json: stripIds(blocks),
        })
        navigate(`/report-templates/${created.id}`, { replace: true })
      } else {
        await updateTemplate.mutateAsync({
          name,
          destination,
          schema_json: stripIds(blocks),
          primary_colour: primaryColour,
          company_name: companyName,
        })
        setDirty(false)
      }
    } finally {
      setSaving(false)
    }
  }

  if (!isNew && isLoading) {
    return (
      <AppShell>
        <div style={{ padding: '40px', color: 'var(--text-muted)', fontSize: '13px' }}>
          Loading template…
        </div>
      </AppShell>
    )
  }

  return (
    <AppShell>
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden', background: 'var(--bg-base)' }}>
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
        <button className="btn btn-ghost btn-sm" onClick={() => navigate('/report-templates', { replace: true })}>
          ← Templates
        </button>

        <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          <input
            className="form-input"
            style={{ width: '220px', fontSize: '14px', fontWeight: 600 }}
            value={name}
            onChange={(e) => { setName(e.target.value); setDirty(true) }}
            placeholder="Template name"
          />
          <div className="select-wrap">
            <select
              className="form-input"
              style={{ width: '140px', fontSize: '13px' }}
              value={destination}
              onChange={(e) => { setDestination(e.target.value); setDirty(true) }}
            >
              {DESTINATION_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>

          {/* Brand settings — only available after save */}
          {!isNew && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', borderLeft: '1px solid var(--border)', paddingLeft: '12px' }}>
              {/* Logo */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                {logoPreview ? (
                  <img
                    src={logoPreview}
                    alt="Logo"
                    style={{ height: '28px', width: 'auto', objectFit: 'contain', cursor: 'pointer', borderRadius: '4px', border: '1px solid var(--border)' }}
                    onClick={() => logoInputRef.current?.click()}
                    title="Click to replace logo"
                  />
                ) : (
                  <button
                    className="btn btn-ghost btn-sm"
                    onClick={() => logoInputRef.current?.click()}
                    disabled={uploadLogo.isPending}
                    title="Upload logo"
                  >
                    {uploadLogo.isPending ? 'Uploading…' : <><img src="/icons/framed_picture_color.svg" width={14} height={14} alt="" aria-hidden="true" style={{ verticalAlign: 'middle', marginRight: 4 }} />Logo</>}
                  </button>
                )}
                <input
                  ref={logoInputRef}
                  type="file"
                  accept="image/png,image/jpeg,image/svg+xml"
                  style={{ display: 'none' }}
                  onChange={handleLogoChange}
                />
              </div>

              {/* Brand colour */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <label style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Colour</label>
                <input
                  type="color"
                  value={primaryColour}
                  onChange={(e) => handleBrandColourChange(e.target.value)}
                  style={{ width: '28px', height: '28px', padding: '2px', border: '1px solid var(--border)', borderRadius: '4px', cursor: 'pointer', background: 'none' }}
                  title="Brand colour"
                />
              </div>

              {/* Company name */}
              <input
                className="form-input"
                style={{ width: '140px', fontSize: '12px' }}
                value={companyName}
                onChange={(e) => handleCompanyNameChange(e.target.value)}
                placeholder="Company name"
                title="Company name shown in reports"
              />
            </div>
          )}
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
            disabled={saving || !name.trim() || (!isNew && !dirty)}
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
    </AppShell>
  )
}
