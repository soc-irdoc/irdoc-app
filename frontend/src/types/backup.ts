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
  /** Fingerprint of the key new backups are encrypted with (#149) */
  key_fingerprint: string
  /** 'secret_key_fallback' = BACKUP_ENCRYPTION_KEY is not set */
  key_source: 'dedicated' | 'secret_key_fallback'
  /** Local backups not yet encrypted with the active key */
  legacy_backup_count: number
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
  key_fingerprint: string | null
  created_at: string
}
