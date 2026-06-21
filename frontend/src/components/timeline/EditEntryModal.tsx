import { useState, useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Modal } from '@/components/common/Modal'
import { Button } from '@/components/common/Button'
import { AttachmentZone } from './AttachmentZone'
import { useUpdateTimelineEntry } from '@/hooks/useTimeline'
import { useAssets, useLinkAssetsToEntry, useUnlinkAssetFromEntry, useEntryAssets } from '@/hooks/useAssets'
import { useUIStore } from '@/stores/uiStore'
import apiClient from '@/lib/apiClient'
import { ASSET_TYPE_ICONS, type AssetType } from '@/types/asset'
import type { TimelineEntry, EntryType, UpdateTimelineEntryPayload, Attachment } from '@/types/timeline'

const ENTRY_TYPES: { value: EntryType; label: string }[] = [
  { value: 'detection', label: 'Detection' },
  { value: 'analysis', label: 'Analysis' },
  { value: 'containment', label: 'Containment' },
  { value: 'evidence', label: 'Evidence' },
  { value: 'comms', label: 'Comms' },
  { value: 'note', label: 'Note' },
]

const LABEL_STYLE: React.CSSProperties = {
  fontSize: 11,
  fontWeight: 600,
  color: 'var(--text-muted)',
  textTransform: 'uppercase',
  letterSpacing: '0.5px',
  marginBottom: 5,
  display: 'block',
}

interface EditEntryModalProps {
  entry: TimelineEntry | null
  incidentId: string
  onClose: () => void
}

export function EditEntryModal({ entry, incidentId, onClose }: EditEntryModalProps) {
  const addToast = useUIStore((s) => s.addToast)
  const qc = useQueryClient()
  const updateEntry = useUpdateTimelineEntry(incidentId)
  const { data: allAssets = [] } = useAssets(incidentId)
  const { data: linkedAssets = [] } = useEntryAssets(incidentId, entry?.id ?? '')
  const linkAssets = useLinkAssetsToEntry(incidentId)
  const unlinkAsset = useUnlinkAssetFromEntry(incidentId)

  const [entryType, setEntryType] = useState<EntryType>('note')
  const [date, setDate] = useState('')
  const [time, setTime] = useState('')
  const [description, setDescription] = useState('')
  const [source, setSource] = useState('')
  const [newFiles, setNewFiles] = useState<File[]>([])
  const [removedAttachmentIds, setRemovedAttachmentIds] = useState<Set<string>>(new Set())
  const [localLinkedAssetIds, setLocalLinkedAssetIds] = useState<Set<string>>(new Set())

  // Initialise form from entry when modal opens
  useEffect(() => {
    if (!entry) return
    const dt = new Date(entry.occurred_at)
    const pad = (n: number) => String(n).padStart(2, '0')
    setEntryType(entry.entry_type)
    setDate(`${dt.getFullYear()}-${pad(dt.getMonth() + 1)}-${pad(dt.getDate())}`)
    setTime(`${pad(dt.getHours())}:${pad(dt.getMinutes())}:${pad(dt.getSeconds())}`)
    setDescription(entry.description)
    setSource(entry.source ?? '')
    setNewFiles([])
    setRemovedAttachmentIds(new Set())
  }, [entry?.id])

  // Sync local asset state when query loads
  useEffect(() => {
    setLocalLinkedAssetIds(new Set(linkedAssets.map((a) => a.id)))
  }, [linkedAssets])

  const visibleAttachments = (entry?.attachments ?? []).filter(
    (att: Attachment) => !removedAttachmentIds.has(att.id)
  )

  async function handleDeleteAttachment(attId: string) {
    try {
      await apiClient.delete(`/incidents/${incidentId}/attachments/${attId}`)
      setRemovedAttachmentIds((prev) => new Set([...prev, attId]))
    } catch {
      addToast('Failed to remove attachment', 'error')
    }
  }

  async function handleToggleAsset(assetId: string) {
    if (!entry) return
    const isLinked = localLinkedAssetIds.has(assetId)
    // Optimistic update
    setLocalLinkedAssetIds((prev) => {
      const next = new Set(prev)
      if (isLinked) next.delete(assetId)
      else next.add(assetId)
      return next
    })
    try {
      if (isLinked) {
        await unlinkAsset.mutateAsync({ assetId, entryId: entry.id })
      } else {
        await linkAssets.mutateAsync({ asset_ids: [assetId], timeline_entry_id: entry.id })
      }
    } catch {
      // Rollback on error
      setLocalLinkedAssetIds((prev) => {
        const next = new Set(prev)
        if (isLinked) next.add(assetId)
        else next.delete(assetId)
        return next
      })
      addToast('Failed to update asset link', 'error')
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!entry || !description.trim()) return

    const occurred_at = `${date}T${time}`
    const payload: UpdateTimelineEntryPayload = {
      entry_type: entryType,
      occurred_at,
      description: description.trim(),
      source: source.trim() || undefined,
    }

    try {
      await updateEntry.mutateAsync({ entryId: entry.id, payload })

      // Upload new attachments sequentially
      for (const file of newFiles) {
        const fd = new FormData()
        fd.append('file', file)
        fd.append('timeline_entry_id', entry.id)
        try {
          await apiClient.post(`/incidents/${incidentId}/attachments`, fd, {
            headers: { 'Content-Type': 'multipart/form-data' },
          })
        } catch {
          addToast(`Failed to upload ${file.name}`, 'error')
        }
      }

      // Refresh timeline to reflect attachment changes made during edit
      qc.invalidateQueries({ queryKey: ['timeline', incidentId] })
      addToast('Entry updated', 'success')
      onClose()
    } catch {
      addToast('Failed to update entry', 'error')
    }
  }

  if (!entry) return null

  return (
    <Modal open={!!entry} onClose={onClose} title="Edit Timeline Entry">
      <form onSubmit={handleSubmit}>
        {/* Row 1: type, date, time, source */}
        <div style={{ display: 'flex', gap: 10, marginBottom: 12, flexWrap: 'wrap' }}>
          <div className="form-group" style={{ minWidth: 130 }}>
            <label style={LABEL_STYLE}>Type</label>
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

          <div className="form-group" style={{ minWidth: 130 }}>
            <label style={LABEL_STYLE}>Date</label>
            <input
              type="date"
              className="form-input"
              value={date}
              onChange={(e) => setDate(e.target.value)}
            />
          </div>

          <div className="form-group" style={{ minWidth: 120 }}>
            <label style={LABEL_STYLE}>Time</label>
            <input
              type="time"
              step="1"
              className="form-input"
              value={time}
              onChange={(e) => setTime(e.target.value)}
            />
          </div>

          <div className="form-group" style={{ flex: 1, minWidth: 140 }}>
            <label style={LABEL_STYLE}>Source</label>
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
            className="form-input"
            placeholder="Describe what happened, what you observed, what actions were taken..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={5}
            style={{ minHeight: 100, fontFamily: 'JetBrains Mono, monospace', lineHeight: 1.6 }}
          />
        </div>

        {/* Existing attachments */}
        {visibleAttachments.length > 0 && (
          <div style={{ marginBottom: 12 }}>
            <label style={LABEL_STYLE}>Existing Attachments</label>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              {visibleAttachments.map((att) => (
                <div
                  key={att.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                    padding: '4px 8px 4px 10px',
                    background: 'var(--bg-elevated)',
                    border: '1px solid var(--border)',
                    borderRadius: 6,
                    fontSize: 11,
                    fontFamily: 'JetBrains Mono, monospace',
                    color: 'var(--text-secondary)',
                  }}
                >
                  <span>{att.original_name}</span>
                  <button
                    type="button"
                    onClick={() => handleDeleteAttachment(att.id)}
                    style={{
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      color: 'var(--red)',
                      fontSize: 13,
                      padding: 0,
                      lineHeight: 1,
                    }}
                    title="Remove attachment"
                    aria-label={`Remove ${att.original_name}`}
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* New attachment upload */}
        <AttachmentZone files={newFiles} onFilesChange={setNewFiles} />

        {/* Asset picker */}
        {allAssets.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <label style={LABEL_STYLE}>🖥️ Linked Assets</label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 4 }}>
              {allAssets.map((asset) => {
                const linked = localLinkedAssetIds.has(asset.id)
                return (
                  <button
                    key={asset.id}
                    type="button"
                    onClick={() => handleToggleAsset(asset.id)}
                    style={{
                      padding: '4px 10px',
                      borderRadius: 6,
                      border: `1px solid ${linked ? 'var(--accent)' : 'var(--border)'}`,
                      background: linked ? 'var(--accent-dim)' : 'var(--bg-card)',
                      color: linked ? 'var(--accent)' : 'var(--text-secondary)',
                      cursor: 'pointer',
                      fontSize: 12,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 5,
                    }}
                  >
                    <span>{ASSET_TYPE_ICONS[asset.asset_type as AssetType] ?? '📦'}</span>
                    <span>{asset.name}</span>
                  </button>
                )
              })}
            </div>
          </div>
        )}

        {/* Actions */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 20 }}>
          <Button type="button" variant="ghost" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="accent"
            size="sm"
            loading={updateEntry.isPending}
            disabled={!description.trim()}
          >
            Save Changes
          </Button>
        </div>
      </form>
    </Modal>
  )
}
