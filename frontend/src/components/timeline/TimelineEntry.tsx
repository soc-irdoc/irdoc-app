import { useCallback, useState } from 'react'
import { useDeleteTimelineEntry, usePinTimelineEntry } from '@/hooks/useTimeline'
import { ENTRY_TYPE_CONFIG } from '@/types/timeline'
import type { TimelineEntry as TEntry, Attachment } from '@/types/timeline'
import { formatDateTime, formatRelative, isImageMime } from '@/lib/utils'
import { useUIStore } from '@/stores/uiStore'
import apiClient from '@/lib/apiClient'
import { ImageLightbox } from '@/components/common/ImageLightbox'
import { PdfPreviewModal } from '@/components/common/PdfPreviewModal'
import { FaClock, FaImage, FaPaperclip, FaPen, FaThumbtack, FaTrashCan } from 'react-icons/fa6'
import { formatMinutes } from '@/lib/timeSpent'

interface TimelineEntryProps {
  entry: TEntry
  incidentId: string
  onEditRequest?: (entry: TEntry) => void
}

const DOT_STYLES: Record<string, { bg: string; border: string }> = {
  detection:   { bg: 'var(--bg-elevated)', border: 'var(--red)' },
  analysis:    { bg: 'var(--bg-elevated)', border: 'var(--blue)' },
  containment: { bg: 'var(--bg-elevated)', border: 'var(--yellow)' },
  evidence:    { bg: 'var(--bg-elevated)', border: 'var(--purple)' },
  comms:       { bg: 'var(--bg-elevated)', border: 'var(--green)' },
  note:        { bg: 'var(--bg-elevated)', border: 'var(--border)' },
}

const BADGE_STYLES: Record<string, { bg: string; color: string }> = {
  detection:   { bg: 'var(--red-dim)',    color: 'var(--red)' },
  analysis:    { bg: 'var(--blue-dim)',   color: 'var(--blue)' },
  containment: { bg: 'var(--yellow-dim)', color: 'var(--yellow)' },
  evidence:    { bg: 'var(--purple-dim)', color: 'var(--purple)' },
  comms:       { bg: 'var(--green-dim)', color: 'var(--green)' },
  note:        { bg: 'var(--bg-elevated)', color: 'var(--text-muted)' },
}

export function TimelineEntryCard({ entry, incidentId, onEditRequest }: TimelineEntryProps) {
  const addToast = useUIStore((s) => s.addToast)
  const deleteEntry = useDeleteTimelineEntry(incidentId)
  const pinEntry = usePinTimelineEntry(incidentId)
  const [hovered, setHovered] = useState(false)
  const [lightboxUrl, setLightboxUrl] = useState<string | null>(null)
  const [pdfPreviewUrl, setPdfPreviewUrl] = useState<string | null>(null)
  const [loadingAttachmentId, setLoadingAttachmentId] = useState<string | null>(null)
  const closeLightbox = useCallback(() => setLightboxUrl(null), [])
  const closePdf = useCallback(() => setPdfPreviewUrl(null), [])

  const config = ENTRY_TYPE_CONFIG[entry.entry_type]
  const dotStyle = DOT_STYLES[entry.entry_type] ?? DOT_STYLES.note
  const badgeStyle = BADGE_STYLES[entry.entry_type] ?? BADGE_STYLES.note

  async function handleDelete() {
    if (!confirm('Delete this timeline entry?')) return
    try {
      await deleteEntry.mutateAsync(entry.id)
      addToast('Entry deleted', 'success')
    } catch {
      addToast('Failed to delete entry', 'error')
    }
  }

  async function handlePin() {
    try {
      await pinEntry.mutateAsync({ entryId: entry.id, pinned: !entry.is_pinned })
    } catch {
      addToast('Failed to pin entry', 'error')
    }
  }

  async function handleAttachmentClick(att: Attachment) {
    if (loadingAttachmentId) return
    setLoadingAttachmentId(att.id)
    try {
      const res = await apiClient.get<{ data: { url: string } }>(
        `/incidents/${incidentId}/attachments/${att.id}/url`
      )
      const url = res.data.data.url
      if (att.mime_type && isImageMime(att.mime_type)) {
        setLightboxUrl(url)
      } else if (att.mime_type === 'application/pdf') {
        setPdfPreviewUrl(url)
      } else {
        const a = document.createElement('a')
        a.href = url
        a.download = att.original_name
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
      }
    } catch {
      addToast('Failed to load attachment', 'error')
    } finally {
      setLoadingAttachmentId(null)
    }
  }

  return (
    <>
      <div
        id={`entry-${entry.id}`}
        className="animate-slide-in"
        style={{ display: 'flex', gap: 20, marginBottom: 20, position: 'relative', scrollMarginTop: 16 }}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      >
        {/* Dot */}
        <div
          style={{
            width: 40,
            height: 40,
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 16,
            flexShrink: 0,
            border: `2px solid ${dotStyle.border}`,
            background: dotStyle.bg,
            marginTop: 2,
            zIndex: 1,
          }}
        >
          <config.icon size={16} aria-hidden="true" style={{ color: dotStyle.border }} />
        </div>

        {/* Card */}
        <div style={{ flex: 1 }}>
          <div
            style={{
              background: 'var(--bg-surface)',
              border: `1px solid ${entry.is_pinned ? 'var(--accent)' : 'var(--border)'}`,
              borderRadius: 12,
              padding: 16,
              transition: 'border-color 0.15s, box-shadow 0.15s',
              boxShadow: entry.is_pinned
                ? 'inset 3px 0 0 var(--accent), 0 0 20px rgba(249,115,22,0.06)'
                : hovered
                ? 'var(--shadow)'
                : 'none',
            }}
          >
            {/* Header */}
            <div
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                justifyContent: 'space-between',
                marginBottom: 10,
                gap: 12,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                {/* Time */}
                <span
                  style={{
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: 12,
                    color: 'var(--accent)',
                    fontWeight: 500,
                  }}
                >
                  {formatDateTime(entry.occurred_at)}
                </span>

                {/* Type badge */}
                <span
                  style={{
                    fontSize: 10,
                    fontWeight: 700,
                    padding: '2px 8px',
                    borderRadius: 4,
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px',
                    background: badgeStyle.bg,
                    color: badgeStyle.color,
                  }}
                >
                  {config.label}
                </span>

                {/* Pin indicator */}
                {entry.is_pinned && (
                  <FaThumbtack size={12} aria-hidden="true" title="Pinned" />
                )}

                {/* Author */}
                {entry.author_name && (
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    by {entry.author_name}
                  </span>
                )}

                {/* Effort (#165) */}
                {entry.time_spent_minutes != null && (
                  <span
                    title="Time spent on this activity"
                    style={{ fontSize: 11, color: 'var(--text-muted)', display: 'inline-flex', alignItems: 'center', gap: 3 }}
                  >
                    <FaClock size={10} aria-hidden="true" /> {formatMinutes(entry.time_spent_minutes)}
                  </span>
                )}

                {/* Source */}
                {entry.source && (
                  <span
                    style={{
                      fontSize: 11,
                      color: 'var(--text-muted)',
                      fontFamily: 'JetBrains Mono, monospace',
                    }}
                  >
                    via {entry.source}
                  </span>
                )}
              </div>

              {/* Actions (visible on hover) */}
              <div
                style={{
                  display: 'flex',
                  gap: 4,
                  opacity: hovered ? 1 : 0,
                  transition: 'opacity 0.15s',
                }}
              >
                {onEditRequest && (
                  <button
                    className="icon-btn"
                    onClick={() => onEditRequest(entry)}
                    aria-label="Edit entry"
                    title="Edit"
                  >
                    <FaPen size={16} aria-hidden="true" />
                  </button>
                )}
                <button
                  className="icon-btn"
                  onClick={handlePin}
                  aria-label={entry.is_pinned ? 'Unpin entry' : 'Pin entry'}
                  title={entry.is_pinned ? 'Unpin' : 'Pin'}
                >
                  <FaThumbtack size={16} aria-hidden="true" />
                </button>
                <button
                  className="icon-btn"
                  onClick={handleDelete}
                  aria-label="Delete entry"
                  title="Delete"
                  style={{ color: 'var(--red)' }}
                >
                  <FaTrashCan size={16} aria-hidden="true" />
                </button>
              </div>
            </div>

            {/* Description */}
            <p
              style={{
                fontSize: 13,
                lineHeight: 1.7,
                color: 'var(--text-primary)',
                fontFamily: 'JetBrains Mono, monospace',
                whiteSpace: 'pre-wrap',
              }}
            >
              {entry.description}
            </p>

            {/* Attachments */}
            {entry.attachments && entry.attachments.length > 0 && (
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 12 }}>
                {entry.attachments.map((att) => (
                  <button
                    key={att.id}
                    className="tl-attach-item"
                    style={{
                      background: 'var(--bg-elevated)',
                      border: '1px solid var(--border)',
                      borderRadius: 8,
                      padding: '6px 10px',
                      fontSize: 11,
                      color: loadingAttachmentId === att.id ? 'var(--text-muted)' : 'var(--text-secondary)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                      cursor: loadingAttachmentId === att.id ? 'wait' : 'pointer',
                      transition: 'all 0.15s',
                      fontFamily: 'JetBrains Mono, monospace',
                      opacity: loadingAttachmentId === att.id ? 0.6 : 1,
                    }}
                    onClick={() => handleAttachmentClick(att)}
                    disabled={loadingAttachmentId === att.id}
                    onMouseEnter={(e) => {
                      if (loadingAttachmentId === att.id) return
                      e.currentTarget.style.borderColor = 'var(--blue)'
                      e.currentTarget.style.color = 'var(--blue)'
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = 'var(--border)'
                      e.currentTarget.style.color = 'var(--text-secondary)'
                    }}
                  >
                    {att.mime_type && isImageMime(att.mime_type)
                      ? <FaImage size={14} aria-hidden="true" />
                      : <FaPaperclip size={14} aria-hidden="true" />}
                    {att.original_name}
                  </button>
                ))}
              </div>
            )}

            {/* Relative time */}
            <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 8 }}>
              {formatRelative(entry.created_at)}
            </p>
          </div>
        </div>
      </div>

      <ImageLightbox url={lightboxUrl} onClose={closeLightbox} />
      <PdfPreviewModal url={pdfPreviewUrl} onClose={closePdf} />

    </>
  )
}
