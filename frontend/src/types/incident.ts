export type Severity = 'critical' | 'high' | 'medium' | 'low'
export type IncidentStatus = 'open' | 'contained' | 'closed' | 'monitoring'
// Final disposition, required to close an incident (#124)
export type Disposition =
  | 'tp_remediated'
  | 'tp_accepted_risk'
  | 'tp_third_party'
  | 'fp_benign'
  | 'fp_tuning_required'
  | 'inconclusive'

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
  disposition: Disposition | null
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
  disposition?: Disposition
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

export const DISPOSITIONS: Disposition[] = [
  'tp_remediated',
  'tp_accepted_risk',
  'tp_third_party',
  'fp_benign',
  'fp_tuning_required',
  'inconclusive',
]

export const DISPOSITION_LABELS: Record<Disposition, string> = {
  tp_remediated: 'True Positive - Remediated / Contained',
  tp_accepted_risk: 'True Positive - Accepted Risk',
  tp_third_party: 'True Positive - Third Party Handled',
  fp_benign: 'False Positive - Benign',
  fp_tuning_required: 'False Positive - Tuning Required',
  inconclusive: 'Unknown - Inconclusive',
}

// Compact form for badges (list rows, header)
export const DISPOSITION_SHORT_LABELS: Record<Disposition, string> = {
  tp_remediated: 'TP - REMEDIATED',
  tp_accepted_risk: 'TP - ACCEPTED RISK',
  tp_third_party: 'TP - THIRD PARTY',
  fp_benign: 'FP - BENIGN',
  fp_tuning_required: 'FP - TUNING',
  inconclusive: 'INCONCLUSIVE',
}

export const DISPOSITION_COLORS: Record<Disposition, string> = {
  tp_remediated: 'chip-green',
  tp_accepted_risk: 'chip-yellow',
  tp_third_party: 'chip-blue',
  fp_benign: 'chip-muted',
  fp_tuning_required: 'chip-purple',
  inconclusive: 'chip-muted',
}
