import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import apiClient from '@/lib/apiClient'
import { useUIStore } from '@/stores/uiStore'
import type { ApiResponse } from '@/types/api'
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
  arrayMove,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'

interface TemplateTask {
  id: string
  title: string
  phase: string
  priority: 'critical' | 'high' | 'medium' | 'low'
  sort_order: number
}

interface IncidentTemplate {
  id: string
  name: string
  slug: string
  is_system: boolean
  is_hidden: boolean
  org_id: string | null
  tasks_json: TemplateTask[]
}

const PRIORITY_COLORS: Record<string, string> = {
  critical: 'chip-red',
  high: 'chip-yellow',
  medium: 'chip-blue',
  low: 'chip-muted',
}

// ── Hooks ──────────────────────────────────────────────────

function useIncidentTemplatesList() {
  return useQuery({
    queryKey: ['incident-templates-admin'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<IncidentTemplate[]>>('/templates/incident')
      return res.data.data
    },
  })
}

function useCreateIncidentTemplate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (payload: Partial<IncidentTemplate>) => {
      const res = await apiClient.post<ApiResponse<IncidentTemplate>>(
        '/templates/incident',
        payload
      )
      return res.data.data
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['incident-templates-admin'] }),
  })
}

function useUpdateIncidentTemplate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: Partial<IncidentTemplate> }) => {
      const res = await apiClient.put<ApiResponse<IncidentTemplate>>(
        `/templates/incident/${id}`,
        payload
      )
      return res.data.data
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['incident-templates-admin'] }),
  })
}

function useDeleteIncidentTemplate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/templates/incident/${id}`)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['incident-templates-admin'] }),
  })
}

function useCloneIncidentTemplate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      const res = await apiClient.post<ApiResponse<IncidentTemplate>>(
        `/templates/incident/${id}/clone`,
        {}
      )
      return res.data.data
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['incident-templates-admin'] }),
  })
}

function useToggleHideIncidentTemplate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, hidden }: { id: string; hidden: boolean }) => {
      const res = await apiClient.put<ApiResponse<IncidentTemplate>>(
        `/templates/incident/${id}`,
        { is_hidden: hidden }
      )
      return res.data.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['incident-templates-admin'] })
      qc.invalidateQueries({ queryKey: ['incident-templates'] })
    },
  })
}

// ── Sortable task row ──────────────────────────────────────

function SortableTaskRow({
  task,
  onUpdate,
  onDelete,
}: {
  task: TemplateTask
  onUpdate: (updates: Partial<TemplateTask>) => void
  onDelete: () => void
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: task.id,
  })

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '8px 0',
    borderBottom: '1px solid var(--border-subtle)',
  }

  return (
    <div ref={setNodeRef} style={style}>
      {/* Drag handle */}
      <button
        className="icon-btn"
        style={{ cursor: 'grab', color: 'var(--text-muted)', flexShrink: 0 }}
        {...attributes}
        {...listeners}
        aria-label="Drag to reorder"
      >
        ◉
      </button>

      {/* Title */}
      <input
        type="text"
        className="form-input"
        style={{ flex: 1 }}
        value={task.title}
        onChange={(e) => onUpdate({ title: e.target.value })}
        placeholder="Task title"
      />

      {/* Priority */}
      <div className="select-wrap" style={{ width: 110 }}>
        <select
          className="form-input"
          value={task.priority}
          onChange={(e) =>
            onUpdate({ priority: e.target.value as TemplateTask['priority'] })
          }
        >
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
      </div>

      {/* Delete */}
      <button
        className="icon-btn"
        style={{ color: 'var(--red)', flexShrink: 0 }}
        onClick={onDelete}
        aria-label="Remove task"
      >
        <img src="/icons/multiply_color.svg" width={14} height={14} alt="" aria-hidden="true" />
      </button>
    </div>
  )
}

// ── Template Editor Panel ──────────────────────────────────

interface EditorProps {
  template: Partial<IncidentTemplate> | null
  onSave: (data: Partial<IncidentTemplate>) => Promise<void>
  onClose: () => void
  saving: boolean
}

function TemplateEditorPanel({ template, onSave, onClose, saving }: EditorProps) {
  const [name, setName] = useState(template?.name ?? '')
  const [slug, setSlug] = useState(template?.slug ?? '')
  const [tasks, setTasks] = useState<TemplateTask[]>(template?.tasks_json ?? [])

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  )

  function generateSlug(n: string) {
    return n
      .toLowerCase()
      .replace(/\s+/g, '-')
      .replace(/[^a-z0-9-]/g, '')
  }

  function handleNameChange(n: string) {
    setName(n)
    if (!template?.id) setSlug(generateSlug(n))
  }

  function getPhases() {
    const phases = [...new Set(tasks.map((t) => t.phase))]
    if (!phases.includes('general')) phases.push('general')
    return phases
  }

  function addTask(phase: string) {
    const newTask: TemplateTask = {
      id: `new-${Date.now()}`,
      title: '',
      phase,
      priority: 'medium',
      sort_order: tasks.filter((t) => t.phase === phase).length,
    }
    setTasks((prev) => [...prev, newTask])
  }

  function addPhase() {
    const phaseName = `phase-${getPhases().length + 1}`
    addTask(phaseName)
  }

  function updateTask(id: string, updates: Partial<TemplateTask>) {
    setTasks((prev) => prev.map((t) => (t.id === id ? { ...t, ...updates } : t)))
  }

  function deleteTask(id: string) {
    setTasks((prev) => prev.filter((t) => t.id !== id))
  }

  function renamePhase(oldName: string, newName: string) {
    const trimmed = newName.trim()
    if (!trimmed || trimmed === oldName) return
    setTasks((prev) => prev.map((t) => t.phase === oldName ? { ...t, phase: trimmed } : t))
  }

  function handleDragEnd(event: DragEndEvent, phase: string) {
    const { active, over } = event
    if (!over || active.id === over.id) return
    const phaseTasks = tasks.filter((t) => t.phase === phase)
    const oldIndex = phaseTasks.findIndex((t) => t.id === active.id)
    const newIndex = phaseTasks.findIndex((t) => t.id === over.id)
    const reordered = arrayMove(phaseTasks, oldIndex, newIndex).map((t, i) => ({
      ...t,
      sort_order: i,
    }))
    setTasks((prev) => [
      ...prev.filter((t) => t.phase !== phase),
      ...reordered,
    ])
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    await onSave({ name, slug, tasks_json: tasks })
  }

  const phases = getPhases()

  return (
    <div
      style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderRadius: 12,
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          padding: '14px 20px',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>
          {template?.id ? `Edit: ${template.name}` : 'New Template'}
        </span>
        <button className="icon-btn" onClick={onClose} aria-label="Close editor">
          <img src="/icons/multiply_color.svg" width={14} height={14} alt="" aria-hidden="true" />
        </button>
      </div>

      <form onSubmit={handleSubmit} style={{ padding: 20 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 20 }}>
          <div>
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
              Template Name
            </label>
            <input
              type="text"
              className="form-input"
              value={name}
              onChange={(e) => handleNameChange(e.target.value)}
              placeholder="e.g. Ransomware Response"
              required
            />
          </div>
          <div>
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
              Slug
            </label>
            <input
              type="text"
              className="form-input"
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
              placeholder="ransomware-response"
              pattern="[a-z0-9-]+"
              required
            />
          </div>
        </div>

        {/* Tasks by phase */}
        {phases.map((phase) => {
          const phaseTasks = tasks
            .filter((t) => t.phase === phase)
            .sort((a, b) => a.sort_order - b.sort_order)

          return (
            <div
              key={phase}
              style={{
                marginBottom: 20,
                border: '1px solid var(--border)',
                borderRadius: 8,
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  padding: '8px 14px',
                  background: 'var(--bg-elevated)',
                  borderBottom: '1px solid var(--border)',
                  fontSize: 11,
                  fontWeight: 700,
                  color: 'var(--text-muted)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <input
                  type="text"
                  defaultValue={phase}
                  onBlur={(e) => renamePhase(phase, e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') e.currentTarget.blur() }}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    outline: 'none',
                    fontSize: 11,
                    fontWeight: 700,
                    color: 'var(--text-muted)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px',
                    width: 'auto',
                    minWidth: 80,
                    cursor: 'text',
                  }}
                />
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  style={{ fontSize: 11, padding: '2px 8px' }}
                  onClick={() => addTask(phase)}
                >
                  + Add Task
                </button>
              </div>

              <div style={{ padding: '0 14px' }}>
                {phaseTasks.length === 0 ? (
                  <div
                    style={{
                      padding: '12px 0',
                      fontSize: 12,
                      color: 'var(--text-muted)',
                      textAlign: 'center',
                    }}
                  >
                    No tasks in this phase
                  </div>
                ) : (
                  <DndContext
                    sensors={sensors}
                    collisionDetection={closestCenter}
                    onDragEnd={(e) => handleDragEnd(e, phase)}
                  >
                    <SortableContext
                      items={phaseTasks.map((t) => t.id)}
                      strategy={verticalListSortingStrategy}
                    >
                      {phaseTasks.map((task) => (
                        <SortableTaskRow
                          key={task.id}
                          task={task}
                          onUpdate={(updates) => updateTask(task.id, updates)}
                          onDelete={() => deleteTask(task.id)}
                        />
                      ))}
                    </SortableContext>
                  </DndContext>
                )}
              </div>
            </div>
          )
        })}

        <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 20 }}>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={addPhase}
          >
            + Add Phase
          </button>
        </div>

        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-accent" disabled={saving}>
            {saving ? 'Saving…' : 'Save Template'}
          </button>
        </div>
      </form>
    </div>
  )
}

// ── Main Page ──────────────────────────────────────────────

export function IncidentTemplatesPage() {
  const addToast = useUIStore((s) => s.addToast)
  const { data: templates = [], isLoading } = useIncidentTemplatesList()
  const createTemplate = useCreateIncidentTemplate()
  const updateTemplate = useUpdateIncidentTemplate()
  const deleteTemplate = useDeleteIncidentTemplate()
  const cloneTemplate = useCloneIncidentTemplate()
  const toggleHide = useToggleHideIncidentTemplate()

  const [editing, setEditing] = useState<Partial<IncidentTemplate> | null>(null)
  const [showEditor, setShowEditor] = useState(false)

  const systemTemplates = templates.filter((t) => t.is_system)
  const orgTemplates = templates.filter((t) => !t.is_system)

  async function handleSave(data: Partial<IncidentTemplate>) {
    try {
      if (editing?.id) {
        await updateTemplate.mutateAsync({ id: editing.id, payload: data })
        addToast('Template updated', 'success')
      } else {
        await createTemplate.mutateAsync(data)
        addToast('Template created', 'success')
      }
      setShowEditor(false)
      setEditing(null)
    } catch {
      addToast('Failed to save template', 'error')
    }
  }

  async function handleClone(id: string) {
    try {
      await cloneTemplate.mutateAsync(id)
      addToast('Template cloned', 'success')
    } catch {
      addToast('Failed to clone template', 'error')
    }
  }

  async function handleDelete(id: string) {
    if (!confirm('Delete this template? This cannot be undone.')) return
    try {
      await deleteTemplate.mutateAsync(id)
      addToast('Template deleted', 'success')
    } catch {
      addToast('Failed to delete template', 'error')
    }
  }

  function handleEdit(t: IncidentTemplate) {
    setEditing(t)
    setShowEditor(true)
  }

  function handleNew() {
    setEditing(null)
    setShowEditor(true)
  }

  const templateRowStyle: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    padding: '12px 20px',
    borderBottom: '1px solid var(--border-subtle)',
    gap: 12,
  }

  if (isLoading) {
    return (
      <div style={{ flex: 1, padding: 24, color: 'var(--text-muted)', fontSize: 13 }}>
        Loading templates…
      </div>
    )
  }

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: 24 }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 24,
        }}
      >
        <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'Syne, sans-serif' }}>
          Incident Templates
        </div>
        <button className="btn btn-accent btn-sm" onClick={handleNew}>
          + New Template
        </button>
      </div>

      {/* Editor panel */}
      {showEditor && (
        <div style={{ marginBottom: 24 }}>
          <TemplateEditorPanel
            template={editing}
            onSave={handleSave}
            onClose={() => {
              setShowEditor(false)
              setEditing(null)
            }}
            saving={createTemplate.isPending || updateTemplate.isPending}
          />
        </div>
      )}

      {/* System Templates */}
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
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}
        >
          System Templates
          <span style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 400 }}>
            Read-only — clone to customise
          </span>
        </div>

        {systemTemplates.map((t) => (
          <div key={t.id} style={templateRowStyle}>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
                {t.name}
              </div>
              <div
                style={{
                  fontSize: 11,
                  color: 'var(--text-muted)',
                  fontFamily: 'JetBrains Mono, monospace',
                  marginTop: 2,
                }}
              >
                {t.slug} · {t.tasks_json?.length ?? 0} tasks
              </div>
            </div>
            <span className="chip chip-muted" style={{ fontSize: 10 }}>
              SYSTEM
            </span>
            {t.is_hidden && (
              <span className="chip chip-muted" style={{ fontSize: 10, opacity: 0.65 }}>HIDDEN</span>
            )}
            <button
              className="btn btn-ghost btn-sm"
              style={{ fontSize: 11, color: 'var(--text-muted)' }}
              onClick={() => toggleHide.mutate({ id: t.id, hidden: !t.is_hidden })}
              disabled={toggleHide.isPending}
              title={t.is_hidden ? 'Restore to incident creation' : 'Hide from incident creation'}
            >
              {t.is_hidden ? 'Unhide' : 'Hide'}
            </button>
            <button
              className="btn btn-ghost btn-sm"
              onClick={() => handleClone(t.id)}
              disabled={cloneTemplate.isPending}
            >
              Clone
            </button>
          </div>
        ))}
      </div>

      {/* Organisation Templates */}
      <div
        style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border)',
          borderRadius: 12,
          overflow: 'hidden',
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
          Organisation Templates
        </div>

        {orgTemplates.length === 0 ? (
          <div
            style={{
              padding: '24px 20px',
              textAlign: 'center',
              color: 'var(--text-muted)',
              fontSize: 13,
            }}
          >
            No custom templates yet. Clone a system template or create a new one.
          </div>
        ) : (
          orgTemplates.map((t) => (
            <div key={t.id} style={templateRowStyle}>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
                  {t.name}
                </div>
                <div
                  style={{
                    fontSize: 11,
                    color: 'var(--text-muted)',
                    fontFamily: 'JetBrains Mono, monospace',
                    marginTop: 2,
                  }}
                >
                  {t.slug} · {t.tasks_json?.length ?? 0} tasks
                </div>
              </div>
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => handleEdit(t)}
              >
                Edit
              </button>
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => handleClone(t.id)}
                disabled={cloneTemplate.isPending}
              >
                Clone
              </button>
              <button
                className="btn btn-danger btn-sm"
                onClick={() => handleDelete(t.id)}
                disabled={deleteTemplate.isPending}
              >
                Delete
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
