// ─── Report Types ─────────────────────────────────────────────────────────────

export type ReportFormat = 'markdown' | 'html' | 'pdf' | 'docx'
export type ReportStatus = 'pending' | 'generating' | 'ready' | 'failed'

export interface Report {
  id: string
  incident_id: string
  report_template_id: string | null
  report_type: string
  destination: string | null
  format: ReportFormat
  classification: string
  generated_by: string | null
  is_ai_assisted: boolean
  status: ReportStatus
  error_message: string | null
  storage_path: string | null
  generated_at: string | null
  created_at: string
}

export interface ReportGenerateRequest {
  report_template_id: string
  format: ReportFormat
  classification: string
  include_ai: boolean
}

export const FORMAT_LABELS: Record<ReportFormat, string> = {
  markdown: 'Markdown',
  html: 'HTML',
  pdf: 'PDF',
  docx: 'Word (DOCX)',
}

export const FORMAT_MIME: Record<ReportFormat, string> = {
  markdown: 'text/markdown',
  html: 'text/html',
  pdf: 'application/pdf',
  docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
}

// ─── Report Template / Block Types ────────────────────────────────────────────

export type BlockType =
  | 'cover'
  | 'section'
  | 'stat_row'
  | 'timeline'
  | 'ioc_table'
  | 'task_list'
  | 'evidence_register'
  | 'text_block'
  | 'divider'
  | 'page_break'
  | 'header'
  | 'tag_list'

export interface ReportBlock {
  id: string          // client-only; not persisted
  type: BlockType
  label?: string
  field?: string
  filter?: string
  stats?: string[]
  columns?: string[]
  show_attachments?: boolean
  show_completed?: boolean
  max_entries?: number
  watermark?: string
  fields?: string[]
  text?: string
  premium?: boolean
}

export interface ReportTemplate {
  id: string
  org_id: string | null
  name: string
  destination: string
  description: string | null
  is_system: boolean
  is_default: boolean
  schema_json: Omit<ReportBlock, 'id'>[]
  created_at: string
  updated_at: string
}

export const BLOCK_LIBRARY: {
  type: BlockType
  label: string
  icon: string
  description: string
  premium?: boolean
  defaultConfig: Partial<Omit<ReportBlock, 'id' | 'type'>>
}[] = [
  {
    type: 'cover',
    label: 'Cover Page',
    icon: '📄',
    description: 'Title page with incident metadata',
    defaultConfig: {
      fields: ['incident.title', 'incident.ref', 'incident.severity', 'incident.status', 'generated_at'],
      watermark: 'CONFIDENTIAL',
    },
  },
  {
    type: 'stat_row',
    label: 'Stat Row',
    icon: '📊',
    description: 'Horizontal row of metric cards',
    defaultConfig: { stats: ['severity', 'status', 'duration', 'affected_users'] },
  },
  {
    type: 'section',
    label: 'Section',
    icon: '📝',
    description: 'Titled text section from a field',
    defaultConfig: { label: 'Executive Summary', field: 'incident.executive_summary' },
  },
  {
    type: 'timeline',
    label: 'Timeline',
    icon: '🕐',
    description: 'Chronological list of entries',
    defaultConfig: { label: 'Full Incident Timeline', filter: 'all', show_attachments: true, max_entries: 0 },
  },
  {
    type: 'ioc_table',
    label: 'IOC Table',
    icon: '🎯',
    description: 'Table of indicators of compromise',
    defaultConfig: { label: 'Indicators of Compromise', filter: 'all', columns: ['type', 'value', 'status'] },
  },
  {
    type: 'task_list',
    label: 'Task List',
    icon: '✅',
    description: 'Response task checklist',
    defaultConfig: { label: 'Response Tasks', filter: 'all', show_completed: true },
  },
  {
    type: 'evidence_register',
    label: 'Evidence Register',
    icon: '📎',
    description: 'Table of uploaded files with hashes',
    defaultConfig: { label: 'Evidence Register' },
  },
  {
    type: 'text_block',
    label: 'Text Block',
    icon: '📋',
    description: 'Free-text or AI-generated narrative',
    defaultConfig: { label: 'Notes', field: 'incident.executive_summary' },
    premium: false,
  },
  {
    type: 'header',
    label: 'Header',
    icon: 'H',
    description: 'Section heading text',
    defaultConfig: { text: 'Section Heading' },
  },
  {
    type: 'tag_list',
    label: 'Tag List',
    icon: '🏷',
    description: 'Renders array fields as chips',
    defaultConfig: { label: 'Attack Vectors', field: 'incident.attack_vector' },
  },
  {
    type: 'divider',
    label: 'Divider',
    icon: '─',
    description: 'Visual separator',
    defaultConfig: {},
  },
  {
    type: 'page_break',
    label: 'Page Break',
    icon: '↵',
    description: 'Forces page break in PDF',
    defaultConfig: {},
  },
]

export const DESTINATION_OPTIONS = [
  { value: 'management', label: 'Management' },
  { value: 'analyst', label: 'Analyst' },
  { value: 'legal', label: 'Legal / Compliance' },
  { value: 'custom', label: 'Custom' },
]

export const CLASSIFICATION_OPTIONS = [
  { value: 'confidential', label: 'CONFIDENTIAL' },
  { value: 'restricted', label: 'RESTRICTED' },
  { value: 'internal', label: 'INTERNAL' },
  { value: 'public', label: 'PUBLIC' },
]

// ─── Sync Policy Types ─────────────────────────────────────────────────────────

export interface SyncPolicy {
  id: string
  incident_id: string
  destination: string
  report_template_id: string | null
  is_active: boolean
  trigger_type: string
  debounce_seconds: number
  last_synced_at: string | null
  last_sync_status: string | null
  last_error: string | null
  created_by: string | null
  created_at: string
}

export interface SyncPolicyCreate {
  destination: string
  report_template_id: string | null
  trigger_type: string
  debounce_seconds: number
  destination_config: Record<string, string>
}
