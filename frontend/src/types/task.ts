export type TaskStatus = 'pending' | 'in_progress' | 'done' | 'skipped'
export type TaskPriority = 'low' | 'medium' | 'high' | 'critical'

export interface Task {
  id: string
  incident_id: string
  title: string
  phase: string
  priority: TaskPriority
  status: TaskStatus
  sort_order: number
  created_at: string
  updated_at: string
}

export interface UpdateTaskPayload {
  status?: TaskStatus
  priority?: TaskPriority
  title?: string
  sort_order?: number
}

export const PRIORITY_COLORS: Record<TaskPriority, string> = {
  low:      'chip-muted',
  medium:   'chip-blue',
  high:     'chip-yellow',
  critical: 'chip-red',
}
