/**
 * /report-templates — lists all system + org templates.
 * Clicking Edit opens the builder for org templates.
 * System templates can be cloned.
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  useReportTemplates,
  useCloneReportTemplate,
  useDeleteReportTemplate,
  useCreateReportTemplate,
  useToggleAiAutoGenerate,
  useToggleHideReportTemplate,
} from '@/hooks/useReportTemplates'
import { DESTINATION_OPTIONS } from '@/types/report'
import { Modal } from '@/components/common/Modal'
import { AppShell } from '@/components/layout/AppShell'

const TEMPLATE_ICONS: Record<string, string> = {
  management: '📊',
  analyst: '🔬',
  legal: '⚖️',
  custom: '✏️',
}

export default function ReportTemplateListPage() {
  const navigate = useNavigate()
  const { data: templates = [], isLoading } = useReportTemplates()
  const cloneTemplate = useCloneReportTemplate()
  const deleteTemplate = useDeleteReportTemplate()
  const createTemplate = useCreateReportTemplate()
  const toggleAi = useToggleAiAutoGenerate()
  const toggleHide = useToggleHideReportTemplate()

  const [showNew, setShowNew] = useState(false)
  const [newName, setNewName] = useState('')
  const [newDest, setNewDest] = useState('custom')

  const handleCreate = async () => {
    if (!newName.trim()) return
    const t = await createTemplate.mutateAsync({
      name: newName.trim(),
      destination: newDest,
      schema_json: [],
    })
    setShowNew(false)
    setNewName('')
    navigate(`/report-templates/${t.id}`)
  }

  const systemTemplates = templates.filter((t) => t.is_system)
  const orgTemplates = templates.filter((t) => !t.is_system)

  return (
    <AppShell>
    <div style={{ padding: '32px 36px', maxWidth: '920px', margin: '0 auto', overflowY: 'auto', flex: 1 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '28px' }}>
        <div>
          <h1 style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '4px' }}>
            Report Templates
          </h1>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            Build custom templates or clone the system defaults to customise.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn btn-accent btn-sm" onClick={() => setShowNew(true)}>
            + New Template
          </button>
        </div>
      </div>

      {/* System Templates */}
      <section style={{ marginBottom: '32px' }}>
        <h2 style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '12px' }}>
          System Templates
        </h2>
        {isLoading ? (
          <div style={{ color: 'var(--text-muted)', fontSize: '13px' }}>Loading…</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {systemTemplates.map((t) => (
              <div
                key={t.id}
                style={{
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border)',
                  borderRadius: '8px',
                  padding: '14px 18px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '14px',
                }}
              >
                <span style={{ fontSize: '22px' }}>{TEMPLATE_ICONS[t.destination] ?? '📋'}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>
                    {t.name}
                    <span className="chip chip-muted" style={{ marginLeft: '8px', fontSize: '10px' }}>SYSTEM</span>
                    {t.is_hidden && (
                      <span className="chip chip-muted" style={{ marginLeft: '4px', fontSize: '10px', opacity: 0.65 }}>HIDDEN</span>
                    )}
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px', textTransform: 'capitalize' }}>
                    {t.destination} · {t.schema_json.length} blocks
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '6px' }}>
                  <button
                    className="btn btn-ghost btn-sm"
                    style={{ fontSize: '11px', color: 'var(--text-muted)' }}
                    onClick={() => toggleHide.mutate({ templateId: t.id, hidden: !t.is_hidden })}
                    disabled={toggleHide.isPending}
                    title={t.is_hidden ? 'Restore to Reports tab' : 'Hide from Reports tab'}
                  >
                    {t.is_hidden ? 'Unhide' : 'Hide'}
                  </button>
                  <button
                    className="btn btn-ghost btn-sm"
                    onClick={() => cloneTemplate.mutate(t.id)}
                    disabled={cloneTemplate.isPending}
                  >
                    Clone
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Org Templates */}
      <section>
        <h2 style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '12px' }}>
          My Templates
        </h2>
        {orgTemplates.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', fontSize: '13px', fontStyle: 'italic' }}>
            No custom templates yet — clone a system template or create a new one.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {orgTemplates.map((t) => (
              <div
                key={t.id}
                style={{
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border)',
                  borderRadius: '8px',
                  padding: '14px 18px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '14px',
                }}
              >
                <span style={{ fontSize: '22px' }}>{TEMPLATE_ICONS[t.destination] ?? '📋'}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {t.name}
                    {t.ai_auto_generate && (
                      <span className="chip" style={{ fontSize: '10px', background: 'var(--accent-subtle, rgba(249,115,22,0.12))', color: 'var(--accent)' }}>AI</span>
                    )}
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px', textTransform: 'capitalize' }}>
                    {t.destination} · {t.schema_json.length} blocks
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                  <button
                    className={`btn btn-sm ${t.ai_auto_generate ? 'btn-accent' : 'btn-ghost'}`}
                    style={{ fontSize: '11px' }}
                    title={t.ai_auto_generate ? 'AI auto-generate ON — click to disable' : 'AI auto-generate OFF — click to enable'}
                    onClick={() => toggleAi.mutate({ templateId: t.id, enabled: !t.ai_auto_generate })}
                    disabled={toggleAi.isPending}
                  >
                    AI {t.ai_auto_generate ? 'On' : 'Off'}
                  </button>
                  <button
                    className="btn btn-ghost btn-sm"
                    onClick={() => navigate(`/report-templates/${t.id}`)}
                  >
                    Edit
                  </button>
                  <button
                    className="btn btn-ghost btn-sm"
                    onClick={() => cloneTemplate.mutate(t.id)}
                    disabled={cloneTemplate.isPending}
                  >
                    Clone
                  </button>
                  <button
                    className="btn btn-danger btn-sm"
                    onClick={() => {
                      if (confirm(`Delete "${t.name}"?`)) deleteTemplate.mutate(t.id)
                    }}
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* New template modal */}
      {showNew && (
        <Modal title="New Report Template" onClose={() => setShowNew(false)} size="sm">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div>
              <label className="form-label" style={{ display: 'block', marginBottom: '6px' }}>Template Name</label>
              <input
                autoFocus
                className="form-input"
                style={{ width: '100%' }}
                placeholder="e.g. Executive Summary"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') handleCreate() }}
              />
            </div>
            <div>
              <label className="form-label" style={{ display: 'block', marginBottom: '6px' }}>Destination</label>
              <div className="select-wrap">
                <select
                  className="form-input"
                  value={newDest}
                  onChange={(e) => setNewDest(e.target.value)}
                >
                  {DESTINATION_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
            </div>
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
              <button className="btn btn-ghost" onClick={() => setShowNew(false)}>Cancel</button>
              <button
                className="btn btn-accent"
                onClick={handleCreate}
                disabled={!newName.trim() || createTemplate.isPending}
              >
                {createTemplate.isPending ? 'Creating…' : 'Create & Edit'}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
    </AppShell>
  )
}
