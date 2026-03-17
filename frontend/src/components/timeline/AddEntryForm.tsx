import { useState, useEffect, useRef } from 'react'
import { useCreateTimelineEntry, useUploadAttachment } from '@/hooks/useTimeline'
import { AttachmentZone } from './AttachmentZone'
import { Button } from '@/components/common/Button'
import { useUIStore } from '@/stores/uiStore'
import { formatNowDate, formatNowTime } from '@/lib/utils'
import type { EntryType } from '@/types/timeline'

const ENTRY_TYPES: { value: EntryType; label: string }[] = [
  { value: 'detection',   label: 'Detection' },
  { value: 'analysis',    label: 'Analysis' },
  { value: 'containment', label: 'Containment' },
  { value: 'evidence',    label: 'Evidence' },
  { value: 'comms',       label: 'Comms' },
  { value: 'note',        label: 'Note' },
]

interface AddEntryFormProps {
  incidentId: string
  inputRef?: React.RefObject<HTMLTextAreaElement>
}

export function AddEntryForm({ incidentId, inputRef }: AddEntryFormProps) {
  const addToast = useUIStore((s) => s.addToast)
  const createEntry = useCreateTimelineEntry(incidentId)

  const [entryType, setEntryType] = useState<EntryType>('note')
  const [date, setDate] = useState(formatNowDate())
  const [time, setTime] = useState(formatNowTime())
  const [description, setDescription] = useState('')
  const [source, setSource] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const [focused, setFocused] = useState(false)

  // Auto-update time when form is focused
  useEffect(() => {
    if (!focused) return
    const interval = setInterval(() => {
      setTime(formatNowTime())
    }, 1000)
    return () => clearInterval(interval)
  }, [focused])

  // Reset date to today on mount
  useEffect(() => {
    setDate(formatNowDate())
  }, [])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!description.trim()) return

    const occurred_at = `${date}T${time}`

    try {
      const entry = await createEntry.mutateAsync({
        entry_type: entryType,
        occurred_at,
        description: description.trim(),
        source: source.trim() || undefined,
      })

      // Upload attachments if any
      if (files.length > 0 && entry?.id) {
        for (const file of files) {
          try {
            const fd = new FormData()
            fd.append('file', file)
            fd.append('timeline_entry_id', entry.id)
            const { default: apiClient } = await import('@/lib/apiClient')
            await apiClient.post(`/incidents/${incidentId}/attachments`, fd, {
              headers: { 'Content-Type': 'multipart/form-data' },
            })
          } catch {
            addToast(`Failed to upload ${file.name}`, 'error')
          }
        }
      }

      // Reset form
      setDescription('')
      setSource('')
      setFiles([])
      setDate(formatNowDate())
      setTime(formatNowTime())
      addToast('Entry added', 'success')
    } catch {
      addToast('Failed to add entry', 'error')
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      onFocus={() => setFocused(true)}
      onBlur={() => setFocused(false)}
      style={{
        background: 'var(--bg-surface)',
        border: `1px dashed ${focused ? 'var(--accent)' : 'var(--border)'}`,
        borderRadius: 12,
        padding: 20,
        marginBottom: 28,
        transition: 'border-color 0.2s',
      }}
    >
      {/* Row 1: type, date, time, source */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 12, flexWrap: 'wrap' }}>
        {/* Type */}
        <div className="form-group" style={{ minWidth: 130 }}>
          <label
            style={{
              fontSize: 11,
              fontWeight: 600,
              color: 'var(--text-muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
              marginBottom: 5,
              display: 'block',
            }}
          >
            Type
          </label>
          <div className="select-wrap">
            <select
              className="form-input form-select"
              value={entryType}
              onChange={(e) => setEntryType(e.target.value as EntryType)}
              style={{ fontFamily: 'Syne, sans-serif' }}
            >
              {ENTRY_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Date */}
        <div className="form-group" style={{ minWidth: 130 }}>
          <label
            style={{
              fontSize: 11,
              fontWeight: 600,
              color: 'var(--text-muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
              marginBottom: 5,
              display: 'block',
            }}
          >
            Date
          </label>
          <input
            type="date"
            className="form-input"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
        </div>

        {/* Time */}
        <div className="form-group" style={{ minWidth: 120 }}>
          <label
            style={{
              fontSize: 11,
              fontWeight: 600,
              color: 'var(--text-muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
              marginBottom: 5,
              display: 'block',
            }}
          >
            Time
          </label>
          <input
            type="time"
            step="1"
            className="form-input"
            value={time}
            onChange={(e) => setTime(e.target.value)}
          />
        </div>

        {/* Source */}
        <div className="form-group" style={{ flex: 1, minWidth: 140 }}>
          <label
            style={{
              fontSize: 11,
              fontWeight: 600,
              color: 'var(--text-muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
              marginBottom: 5,
              display: 'block',
            }}
          >
            Source
          </label>
          <input
            type="text"
            className="form-input"
            placeholder="SIEM alert, Splunk, email..."
            value={source}
            onChange={(e) => setSource(e.target.value)}
          />
        </div>
      </div>

      {/* Description */}
      <div style={{ marginBottom: 12 }}>
        <textarea
          ref={inputRef}
          className="form-input"
          placeholder="Describe what happened, what you observed, what actions were taken..."
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={4}
          style={{ minHeight: 90, fontFamily: 'JetBrains Mono, monospace', lineHeight: 1.6 }}
        />
      </div>

      {/* Attachment zone */}
      <AttachmentZone files={files} onFilesChange={setFiles} />

      {/* Actions */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 14 }}>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => {
            setDescription('')
            setSource('')
            setFiles([])
          }}
        >
          Clear
        </Button>
        <Button
          type="submit"
          variant="accent"
          size="sm"
          loading={createEntry.isPending}
          disabled={!description.trim()}
        >
          Add Entry
        </Button>
      </div>
    </form>
  )
}
