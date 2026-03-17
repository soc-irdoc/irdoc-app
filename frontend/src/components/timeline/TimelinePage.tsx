import { useRef, useState, useEffect } from 'react'
import { useTimeline } from '@/hooks/useTimeline'
import { AddEntryForm } from './AddEntryForm'
import { TimelineEntryCard } from './TimelineEntry'
import { TimelineFilters } from './TimelineFilters'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { EmptyState } from '@/components/common/EmptyState'
import { getSocket, joinIncident, leaveIncident } from '@/lib/websocket'
import { useQueryClient } from '@tanstack/react-query'
import apiClient from '@/lib/apiClient'
import type { EntryType } from '@/types/timeline'

interface TimelinePageProps {
  incidentId: string
}

export function TimelinePage({ incidentId }: TimelinePageProps) {
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const [typeFilter, setTypeFilter] = useState<EntryType | 'all'>('all')
  const qc = useQueryClient()

  const { data: entries = [], isLoading } = useTimeline(
    incidentId,
    typeFilter !== 'all' ? { entry_type: typeFilter } : undefined
  )

  // WebSocket: join incident room and listen for real-time updates
  useEffect(() => {
    joinIncident(incidentId)
    const socket = getSocket()

    const handlers: Array<[string, () => void]> = [
      ['timeline:entry:added', () => qc.invalidateQueries({ queryKey: ['timeline', incidentId] })],
      ['timeline:entry:updated', () => qc.invalidateQueries({ queryKey: ['timeline', incidentId] })],
      ['timeline:entry:deleted', () => qc.invalidateQueries({ queryKey: ['timeline', incidentId] })],
    ]
    handlers.forEach(([event, handler]) => socket.on(event, handler))

    return () => {
      leaveIncident(incidentId)
      handlers.forEach(([event, handler]) => socket.off(event, handler))
    }
  }, [incidentId, qc])

  // Keyboard shortcut: N → focus add entry
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'n' && !e.ctrlKey && !e.metaKey && e.target === document.body) {
        e.preventDefault()
        inputRef.current?.focus()
      }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [])

  async function handleExportCSV() {
    const res = await apiClient.get(`/incidents/${incidentId}/timeline/export`, {
      responseType: 'blob',
    })
    const url = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = url
    a.download = `timeline-${incidentId}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ flex: 1, overflowY: 'auto', padding: 24 }}>
        {/* Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: 20,
          }}
        >
          <h2
            style={{
              fontSize: 18,
              fontWeight: 800,
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              color: 'var(--text-primary)',
            }}
          >
            ⏱ Timeline{' '}
            <span style={{ color: 'var(--text-muted)', fontSize: 13, fontWeight: 500 }}>
              {entries.length} entries
            </span>
          </h2>
        </div>

        {/* Add Entry Form */}
        <AddEntryForm incidentId={incidentId} inputRef={inputRef} />

        {/* Filters */}
        <TimelineFilters
          active={typeFilter}
          onChange={setTypeFilter}
          onExportCSV={handleExportCSV}
        />

        {/* Timeline */}
        {isLoading ? (
          <div className="flex justify-center py-12">
            <LoadingSpinner />
          </div>
        ) : entries.length === 0 ? (
          <EmptyState
            icon="⏱"
            title="No timeline entries"
            description='Add your first entry above or press "N" to focus the form.'
          />
        ) : (
          <div
            style={{
              position: 'relative',
            }}
          >
            {/* Timeline vertical line */}
            <div
              style={{
                position: 'absolute',
                left: 20,
                top: 0,
                bottom: 0,
                width: 2,
                background: 'linear-gradient(to bottom, var(--accent), var(--border))',
                borderRadius: 2,
              }}
            />
            {entries.map((entry) => (
              <TimelineEntryCard
                key={entry.id}
                entry={entry}
                incidentId={incidentId}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
