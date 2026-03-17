import { useState } from 'react'
import { useDeleteTimelineEntry, usePinTimelineEntry } from '@/hooks/useTimeline'
import { ENTRY_TYPE_CONFIG } from '@/types/timeline'
import type { TimelineEntry as TEntry } from '@/types/timeline'
import { formatDateTime, formatRelative, isImageMime } from '@/lib/utils'
import { useUIStore } from '@/stores/uiStore'

interface TimelineEntryProps {
  entry: TEntry
  incidentId: string
}

const DOT_STYLES: Record<string, { bg: string; border: string }> = {
  detection:   { bg: 'var(--red-dim)',    border: 'var(--red)' },
  analysis:    { bg: 'var(--blue-dim)',   border: 'var(--blue)' },
  containment: { bg: 'var(--yellow-dim)', border: 'var(--yellow)' },
  evidence:    { bg: 'var(--purple-dim)', border: 'var(--purple)' },
  comms:       { bg: 'var(--green-dim)', border: 'var(--green)' },
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

export function TimelineEntryCard({ entry, incidentId }: TimelineEntryProps) {
  const addToast = useUIStore((s) => s.addToast)
  const deleteEntry = useDeleteTimelineEntry(incidentId)
  const pinEntry = usePinTimelineEntry(incidentId)
  const [hovered, setHovered] = useState(false)
  const [lightboxUrl, setLightboxUrl] = useState<string | null>(null)

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

  return (
    <>
      <div
        className="animate-slide-in"
        style={{ display: 'flex', gap: 20, marginBottom: 20, position: 'relative' }}
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
          {config.icon}
        </div>

        {/* Card */}
        <div style={{ flex: 1 }}>
          <div
            style={{
              background: 'var(--bg-surface)',
              border: `1px solid ${entry.is_pinned ? 'var(--accent)' : 'var(--border)'}`,
              borderLeft: entry.is_pinned ? '3px solid var(--accent)' : undefined,
              borderRadius: 12,
              padding: 16,
              transition: 'border-color 0.15s',
              boxShadow: hovered ? 'var(--shadow)' : 'none',
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
                  <span style={{ fontSize: 12 }} title="Pinned">📌</span>
                )}

                {/* Author */}
                {entry.author_name && (
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    by {entry.author_name}
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
                <button
                  className="icon-btn"
                  onClick={handlePin}
                  aria-label={entry.is_pinned ? 'Unpin entry' : 'Pin entry'}
                  title={entry.is_pinned ? 'Unpin' : 'Pin'}
                >
                  📌
                </button>
                <button
                  className="icon-btn"
                  onClick={handleDelete}
                  aria-label="Delete entry"
                  title="Delete"
                  style={{ color: 'var(--red)' }}
                >
                  🗑
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
                      color: 'var(--text-secondary)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                      cursor: 'pointer',
                      transition: 'all 0.15s',
                      fontFamily: 'JetBrains Mono, monospace',
                    }}
                    onClick={() => {
                      if (isImageMime(att.mime_type) && att.url) {
                        setLightboxUrl(att.url)
                      } else if (att.url) {
                        window.open(att.url, '_blank')
                      }
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = 'var(--blue)'
                      e.currentTarget.style.color = 'var(--blue)'
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = 'var(--border)'
                      e.currentTarget.style.color = 'var(--text-secondary)'
                    }}
                  >
                    <span>{isImageMime(att.mime_type) ? '🖼' : '📎'}</span>
                    {att.original_filename}
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

      {/* Lightbox */}
      {lightboxUrl && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 200,
            background: 'rgba(0,0,0,0.85)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 24,
          }}
          onClick={() => setLightboxUrl(null)}
        >
          <img
            src={lightboxUrl}
            alt="Attachment"
            style={{ maxWidth: '90vw', maxHeight: '90vh', borderRadius: 8 }}
          />
        </div>
      )}
    </>
  )
}
