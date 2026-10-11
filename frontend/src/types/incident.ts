export type Severity = 'critical' | 'high' | 'medium' | 'low'
export type IncidentStatus = 'open' | 'contained' | 'closed' | 'monitoring'

export interface UserBrief {
  id: string
  full_name: string
  email: string
  avatar_initials: string | null
}

export interface IncidentExternalRef {
  id: string
  incident_id: string
  external_source: string
  external_ref: string
  external_url: string | null
}

export interface Incident {
  id: string
  org_id: string
  incident_ref: string
  title: string
  severity: Severity
  status: IncidentStatus
  assigned_to: string | null
  assigned_user: UserBrief | null
  executive_summary: string | null
  notes: string | null
  lessons_learned: string | null
  actions_todo: string | null
  attack_vector: string[]
  affected_users: number
  metadata: Record<string, unknown>
  created_at: string
  updated_at: string
  contained_at: string | null
  closed_at: string | null
  external_refs: IncidentExternalRef[]
  ai_summary?: string | null
  ai_recommendations?: string | null
}

export interface IncidentStats {
  timeline_count: number
  ioc_count: number
  task_total: number
  task_done: number
  attachment_count: number
}

export interface CreateIncidentPayload {
  title: string
  severity: Severity
  template_id?: string
  assigned_to?: string
}

export interface UpdateIncidentPayload {
  title?: string
  severity?: Severity
  status?: IncidentStatus
  executive_summary?: string | null
  notes?: string | null
  lessons_learned?: string | null
  actions_todo?: string | null
  attack_vector?: string[]
  affected_users?: number
  assigned_to?: string | null
}

export const SEVERITIES: Severity[] = ['critical', 'high', 'medium', 'low']

export const SEVERITY_LABELS: Record<Severity, string> = {
  critical: 'CRITICAL',
  high: 'HIGH',
  medium: 'MEDIUM',
  low: 'LOW',
}

export const SEVERITY_COLORS: Record<Severity, string> = {
  critical: 'chip-crimson',
  high: 'chip-red',
  medium: 'chip-yellow',
  low: 'chip-blue',
}

export const STATUS_LABELS: Record<IncidentStatus, string> = {
  open: 'OPEN',
  contained: 'CONTAINED',
  closed: 'CLOSED',
  monitoring: 'MONITORING',
}

export const STATUS_COLORS: Record<IncidentStatus, string> = {
  open: 'chip-red',
  contained: 'chip-yellow',
  closed: 'chip-green',
  monitoring: 'chip-blue',
}
