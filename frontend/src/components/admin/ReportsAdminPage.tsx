import { useState, useRef } from 'react'
import {
  useDocxTemplates,
  useDownloadBaseTemplate,
  useUploadDocxTemplate,
  useSetDefaultDocxTemplate,
  useRenameDocxTemplate,
  useDeleteDocxTemplate,
} from '@/hooks/useDocxTemplates'
import { useUIStore } from '@/stores/uiStore'
import { Button } from '@/components/common/Button'
import type { DocxTemplate } from '@/types/docxTemplate'

function fmtSize(bytes: number | null) {
  if (!bytes) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

export function ReportsAdminPage() {
  const addToast = useUIStore((s) => s.addToast)
  const { data: templates = [], isLoading } = useDocxTemplates()
  const downloadBase = useDownloadBaseTemplate()
  const upload = useUploadDocxTemplate()
  const setDefault = useSetDefaultDocxTemplate()
  const rename = useRenameDocxTemplate()
  const del = useDeleteDocxTemplate()

  const [uploadName, setUploadName] = useState('')
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [renamingId, setRenamingId] = useState<string | null>(null)
  const [renameVal, setRenameVal] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  async function handleUpload() {
    if (!uploadName.trim() || !uploadFile) return
    try {
      await upload.mutateAsync({ name: uploadName.trim(), file: uploadFile })
      setUploadName('')
      setUploadFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
      addToast('Template uploaded', 'success')
    } catch {
      addToast('Upload failed', 'error')
    }
  }

  async function handleSetDefault(t: DocxTemplate) {
    try {
      await setDefault.mutateAsync(t.id)
      addToast(`"${t.name}" set as default`, 'success')
    } catch {
      addToast('Failed to set default', 'error')
    }
  }

  async function handleRename(id: string) {
    if (!renameVal.trim()) return
    try {
      await rename.mutateAsync({ id, name: renameVal.trim() })
      setRenamingId(null)
      addToast('Renamed', 'success')
    } catch {
      addToast('Rename failed', 'error')
    }
  }

  async function handleDelete(t: DocxTemplate) {
    if (!confirm(`Delete template "${t.name}"?`)) return
    try {
      await del.mutateAsync(t.id)
      addToast('Template deleted', 'success')
    } catch {
      addToast('Delete failed', 'error')
    }
  }

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: 28 }}>
      <h2 style={{ fontSize: 18, fontWeight: 800, color: 'var(--text-primary)', marginBottom: 6 }}>
        Report Templates
      </h2>
      <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 28, lineHeight: 1.6 }}>
        Manage DOCX report templates used to generate incident reports.
        Download the base template, customise it in Word (add your logo, adjust styles),
        then upload it back.
      </p>

      {/* Base template download */}
      <section style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderRadius: 12,
        padding: 20,
        marginBottom: 24,
      }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 8 }}>
          📥 Base Template
        </h3>
        <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 16, lineHeight: 1.6 }}>
          Download the base DOCX scaffold. It includes every section and all{' '}
          <code style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: 'var(--accent)' }}>
            {'{{PLACEHOLDER}}'}
          </code>{' '}
          markers that are replaced with real incident data at report generation time.
          Customise the document in Word (add your company logo, change fonts and colours,
          adjust page layout), then upload it below. Do not remove or rename the placeholders.
        </p>
        <Button
          variant="accent"
          size="sm"
          loading={downloadBase.isPending}
          onClick={() => downloadBase.mutate()}
        >
          ⬇ Download Base Template
        </Button>
      </section>

      {/* Upload section */}
      <section style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderRadius: 12,
        padding: 20,
        marginBottom: 24,
      }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 16 }}>
          ⬆ Upload Custom Template
        </h3>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 200 }}>
            <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Template Name
            </label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. ACME Corp Template"
              value={uploadName}
              onChange={(e) => setUploadName(e.target.value)}
              style={{ minWidth: 200 }}
            />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              DOCX File
            </label>
            <input
              ref={fileInputRef}
              type="file"
              accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
              style={{ fontSize: 13, color: 'var(--text-secondary)' }}
            />
          </div>
          <Button
            variant="accent"
            size="sm"
            loading={upload.isPending}
            disabled={!uploadName.trim() || !uploadFile}
            onClick={handleUpload}
          >
            Upload
          </Button>
        </div>
        {uploadFile && (
          <p style={{ marginTop: 8, fontSize: 12, color: 'var(--text-muted)' }}>
            Selected: {uploadFile.name} ({fmtSize(uploadFile.size)})
          </p>
        )}
      </section>

      {/* Templates list */}
      <section>
        <h3 style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 14 }}>
          📋 Your Templates
        </h3>

        {isLoading ? (
          <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>Loading…</p>
        ) : templates.length === 0 ? (
          <div style={{
            padding: '32px 20px',
            textAlign: 'center',
            border: '1px dashed var(--border)',
            borderRadius: 10,
            color: 'var(--text-muted)',
            fontSize: 13,
          }}>
            No templates yet. Upload one above or download the base template to get started.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {templates.map((t) => (
              <div
                key={t.id}
                style={{
                  background: 'var(--bg-surface)',
                  border: `1px solid ${t.is_default ? 'var(--accent)' : 'var(--border)'}`,
                  borderRadius: 10,
                  padding: '14px 18px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 14,
                }}
              >
                <span style={{ fontSize: 20, flexShrink: 0 }}>📄</span>

                <div style={{ flex: 1, minWidth: 0 }}>
                  {renamingId === t.id ? (
                    <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                      <input
                        type="text"
                        className="form-input"
                        value={renameVal}
                        onChange={(e) => setRenameVal(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleRename(t.id)
                          if (e.key === 'Escape') setRenamingId(null)
                        }}
                        autoFocus
                        style={{ fontSize: 13, maxWidth: 260 }}
                      />
                      <Button size="sm" variant="accent" onClick={() => handleRename(t.id)}>Save</Button>
                      <Button size="sm" variant="ghost" onClick={() => setRenamingId(null)}>Cancel</Button>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>
                        {t.name}
                      </span>
                      {t.is_default && (
                        <span className="chip chip-green" style={{ fontSize: 10 }}>DEFAULT</span>
                      )}
                    </div>
                  )}
                  <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                    {fmtSize(t.file_size)} · Uploaded {new Date(t.created_at).toLocaleDateString()}
                  </p>
                </div>

                <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                  {!t.is_default && (
                    <button
                      className="btn btn-ghost btn-sm"
                      onClick={() => handleSetDefault(t)}
                      disabled={setDefault.isPending}
                    >
                      Set Default
                    </button>
                  )}
                  <button
                    className="btn btn-ghost btn-sm"
                    onClick={() => {
                      setRenamingId(t.id)
                      setRenameVal(t.name)
                    }}
                  >
                    Rename
                  </button>
                  <button
                    className="btn btn-ghost btn-sm"
                    style={{ color: 'var(--status-red)' }}
                    onClick={() => handleDelete(t)}
                    disabled={del.isPending}
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
