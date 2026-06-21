export type EntryType = 'detection' | 'analysis' | 'containment' | 'evidence' | 'comms' | 'note'

export interface Attachment {
  id: string
  original_name: string
  mime_type: string | null
  file_size: number | null
  sha256: string
}

export interface TimelineEntry {
  id: string
  incident_id: string
  author_id: string
  author_name?: string
  entry_type: EntryType
  occurred_at: string
  description: string
  source: string | null
  is_pinned: boolean
  metadata: Record<string, unknown>
  created_at: string
  attachments?: Attachment[]
}

export interface CreateTimelineEntryPayload {
  entry_type: EntryType
  occurred_at: string
  description: string
  source?: string
}

export interface UpdateTimelineEntryPayload {
  entry_type?: EntryType
  occurred_at?: string
  description?: string
  source?: string
}

export const ENTRY_TYPE_CONFIG: Record<EntryType, {
  label: string
  dotClass: string
  badgeClass: string
  icon: string
}> = {
  detection: {
    label: 'Detection',
    dotClass: 'dot-detection',
    badgeClass: 'badge-detection',
    icon: '🔍',
  },
  analysis: {
    label: 'Analysis',
    dotClass: 'dot-analysis',
    badgeClass: 'badge-analysis',
    icon: '🔬',
  },
  containment: {
    label: 'Containment',
    dotClass: 'dot-containment',
    badgeClass: 'badge-containment',
    icon: '🛡️',
  },
  evidence: {
    label: 'Evidence',
    dotClass: 'dot-evidence',
    badgeClass: 'badge-evidence',
    icon: '📎',
  },
  comms: {
    label: 'Comms',
    dotClass: 'dot-comms',
    badgeClass: 'badge-comms',
    icon: '💬',
  },
  note: {
    label: 'Note',
    dotClass: 'dot-note',
    badgeClass: 'badge-note',
    icon: '📝',
  },
}
