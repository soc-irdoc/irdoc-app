import type { UserBrief } from './incident'

export interface DashboardRecentIncident {
  id: string
  incident_ref: string
  title: string
  severity: string
  status: string
  created_at: string
  assigned_user: UserBrief | null
}

export interface DashboardTeamMember {
  user_id: string
  full_name: string
  avatar_initials: string
  open_count: number
}

export interface DashboardMyTask {
  id: string
  title: string
  priority: string
  incident_id: string
  incident_ref: string
}

export interface DashboardStats {
  incidents: {
    by_status: Record<string, number>
    by_severity: Record<string, number>
    total: number
    recent: DashboardRecentIncident[]
  }
  team_workload: DashboardTeamMember[]
  resolved_count: number
  my_stats?: {
    assigned_count: number
    pending_tasks: number
    recent_tasks: DashboardMyTask[]
  }
  led_cases?: {
    count: number
    unassigned_count: number
    recent: Array<{ id: string; incident_ref: string; title: string; severity: string }>
  }
  attack_vectors?: Array<{ vector: string; count: number }>
  org_health?: {
    active_users: number
    mfa_enabled_count: number
    pending_invites: number
    total_integrations: number
    active_integrations: number
  }
  recent_audit?: Array<{
    action: string
    entity_type: string
    created_at: string
    user_email: string
  }>
}
