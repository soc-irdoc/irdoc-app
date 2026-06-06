export interface BackupConfig {
  id: string
  enabled: boolean
  schedule: '6h' | 'daily' | 'weekly' | 'monthly'
  retention_days: number
  destination: 'local' | 'cloud'
  last_backup_at: string | null
  last_backup_status: 'success' | 'failed' | 'running' | null
  last_backup_error: string | null
  last_backup_size_bytes: number | null
}

export interface BackupConfigUpdate {
  enabled?: boolean
  schedule?: '6h' | 'daily' | 'weekly' | 'monthly'
  retention_days?: number
  destination?: 'local' | 'cloud'
}

export interface BackupRecord {
  id: string
  filename: string
  size_bytes: number | null
  destination: string
  status: 'success' | 'failed'
  error: string | null
  created_at: string
}
