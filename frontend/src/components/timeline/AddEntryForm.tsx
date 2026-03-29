import { useState, useEffect } from 'react'
import { useCreateTimelineEntry } from '@/hooks/useTimeline'
import { useAssets, useLinkAssetsToEntry } from '@/hooks/useAssets'
import { AttachmentZone } from './AttachmentZone'
import { Button } from '@/components/common/Button'
import { useUIStore } from '@/stores/uiStore'
import { formatNowDate, formatNowTime } from '@/lib/utils'
import type { EntryType } from '@/types/timeline'
import { ASSET_TYPE_ICONS, ASSET_TYPE_LABELS, type AssetType } from '@/types/asset'

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
  const { data: allAssets = [] } = useAssets(incidentId)
  const linkAssets = useLinkAssetsToEntry(incidentId)

  const [entryType, setEntryType] = useState<EntryType>('note')
  const [date, setDate] = useState(formatNowDate())
  const [time, setTime] = useState(formatNowTime())
  const [description, setDescription] = useState('')
  const [source, setSource] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const [focused, setFocused] = useState(false)
  const [assetPickerOpen, setAssetPickerOpen] = useState(false)
  const [selectedAssetIds, setSelectedAssetIds] = useState<Set<string>>(new Set())

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

      // Upload attachments if any — track successes and failures for a consolidated toast
      let uploadedCount = 0
      let failedCount = 0
      if (files.length > 0 && entry?.id) {
        const { default: apiClient } = await import('@/lib/apiClient')
        for (const file of files) {
          try {
            const fd = new FormData()
            fd.append('file', file)
            fd.append('timeline_entry_id', entry.id)
            await apiClient.post(`/incidents/${incidentId}/attachments`, fd, {
              headers: { 'Content-Type': 'multipart/form-data' },
            })
            uploadedCount++
          } catch {
            failedCount++
          }
        }
      }

      // Link selected assets to the entry
      if (selectedAssetIds.size > 0 && entry?.id) {
        try {
          await linkAssets.mutateAsync({
            asset_ids: Array.from(selectedAssetIds),
            timeline_entry_id: entry.id,
          })
        } catch {
          addToast('Entry added but failed to link assets', 'error')
        }
      }

      // Reset form
      setDescription('')
      setSource('')
      setFiles([])
      setDate(formatNowDate())
      setTime(formatNowTime())
      setSelectedAssetIds(new Set())
      setAssetPickerOpen(false)

      // Consolidated result toast — include attachment outcome when files were queued
      if (files.length === 0) {
        addToast('Entry added', 'success')
      } else if (failedCount === 0) {
        addToast(`Entry added. ${uploadedCount} attachment${uploadedCount !== 1 ? 's' : ''} uploaded.`, 'success')
      } else {
        addToast(
          `Entry added. ${uploadedCount} of ${files.length} attachment${files.length !== 1 ? 's' : ''} uploaded — ${failedCount} failed.`,
          'error',
        )
      }
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

      {/* Asset picker */}
      {allAssets.length > 0 && (
        <div style={{ marginTop: 10 }}>
          <button
            type="button"
            onClick={() => setAssetPickerOpen(o => !o)}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-muted)',
              fontSize: 12,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              padding: '4px 0',
            }}
          >
            🖥️ Link assets{selectedAssetIds.size > 0 ? ` (${selectedAssetIds.size} selected)` : ''}
            {' '}
            <span style={{ fontSize: 10 }}>{assetPickerOpen ? '▲' : '▼'}</span>
          </button>
          {assetPickerOpen && (
            <div style={{
              marginTop: 6,
              display: 'flex',
              flexWrap: 'wrap',
              gap: 6,
              padding: '10px 12px',
              background: 'var(--bg-base)',
              borderRadius: 8,
              border: '1px solid var(--border-subtle)',
            }}>
              {allAssets.map(asset => {
                const selected = selectedAssetIds.has(asset.id)
                return (
                  <button
                    key={asset.id}
                    type="button"
                    onClick={() => {
                      setSelectedAssetIds(prev => {
                        const next = new Set(prev)
                        if (next.has(asset.id)) next.delete(asset.id)
                        else next.add(asset.id)
                        return next
                      })
                    }}
                    style={{
                      padding: '4px 10px',
                      borderRadius: 6,
                      border: `1px solid ${selected ? 'var(--accent)' : 'var(--border)'}`,
                      background: selected ? 'var(--accent-dim)' : 'var(--bg-card)',
                      color: selected ? 'var(--accent)' : 'var(--text-secondary)',
                      cursor: 'pointer',
                      fontSize: 12,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 5,
                    }}
                  >
                    <span>{ASSET_TYPE_ICONS[asset.asset_type as AssetType] ?? '📦'}</span>
                    <span>{asset.name}</span>
                    <span style={{ fontSize: 10, opacity: 0.6 }}>
                      {ASSET_TYPE_LABELS[asset.asset_type as AssetType]}
                    </span>
                  </button>
                )
              })}
            </div>
          )}
        </div>
      )}

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
            setSelectedAssetIds(new Set())
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
