import { useEffect, useRef, useState } from 'react'
import { FaPen } from 'react-icons/fa6'

interface EditableTitleProps {
  title: string
  canEdit: boolean
  /** Save the new title; reject to keep the editor open. */
  onSave: (title: string) => Promise<void>
}

const MAX_LENGTH = 500

// The incident title in the workspace header, renamable in place (#125).
// Click it (or the pencil) to edit; Enter or leaving the field saves, Escape
// cancels. A blank title is not saved.
export function EditableTitle({ title, canEdit, onSave }: EditableTitleProps) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(title)
  const [saving, setSaving] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  // Enter saves and then blurs; the blur must not save a second time.
  const done = useRef(false)

  useEffect(() => {
    if (!editing) setDraft(title)
  }, [title, editing])

  useEffect(() => {
    if (editing) inputRef.current?.select()
  }, [editing])

  function start() {
    if (!canEdit) return
    done.current = false
    setDraft(title)
    setEditing(true)
  }

  function cancel() {
    done.current = true
    setEditing(false)
  }

  async function commit() {
    if (done.current) return
    const next = draft.trim()
    if (!next || next === title) {
      cancel()
      return
    }
    done.current = true
    setSaving(true)
    try {
      await onSave(next)
      setEditing(false)
    } catch {
      done.current = false
      inputRef.current?.focus()
    } finally {
      setSaving(false)
    }
  }

  const headingStyle: React.CSSProperties = {
    fontSize: 17,
    fontWeight: 800,
    color: 'var(--text-primary)',
    letterSpacing: '-0.01em',
  }

  if (editing) {
    return (
      <input
        ref={inputRef}
        className="form-input"
        aria-label="Incident title"
        value={draft}
        maxLength={MAX_LENGTH}
        disabled={saving}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            e.preventDefault()
            commit()
          } else if (e.key === 'Escape') {
            e.preventDefault()
            cancel()
          }
        }}
        style={{ ...headingStyle, flex: 1, minWidth: 0, padding: '4px 8px' }}
      />
    )
  }

  return (
    <div className="editable-title" style={{ flex: 1, minWidth: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
      <h1
        title={canEdit ? `${title} (click to rename)` : title}
        onClick={start}
        style={{
          ...headingStyle,
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          cursor: canEdit ? 'text' : 'default',
        }}
      >
        {title}
      </h1>
      {canEdit && (
        <button
          type="button"
          className="icon-btn editable-title-pen"
          onClick={start}
          aria-label="Rename incident"
          title="Rename incident"
        >
          <FaPen size={11} aria-hidden="true" />
        </button>
      )}
    </div>
  )
}
