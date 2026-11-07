export interface BackupConfig {
  id: string
  enabled: boolean
  schedule: '6h' | 'daily' | 'weekly' | 'monthly'
  retention_days: number
  destination: 'local' | 'cloud' | 'sftp' | 'smb'
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
  destination?: 'local' | 'cloud' | 'sftp' | 'smb'
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

// SFTP / SMB destinations (#151)
export type RemoteBackupKind = 'sftp' | 'smb'

export interface SFTPConfigPayload {
  host: string
  port: number
  username: string
  remote_dir: string
  auth: 'password' | 'key'
  password?: string
  private_key?: string
  passphrase?: string
  /** OpenSSH public key line: pins the server's host key */
  host_key?: string
}

export interface SMBConfigPayload {
  server: string
  port: number
  share: string
  path: string
  username: string
  password?: string
  domain?: string
  require_encryption: boolean
}

/** What the API returns: settings without secrets, plus *_set flags. */
export interface RemoteBackupConfig {
  kind: RemoteBackupKind
  configured: boolean
  host?: string
  server?: string
  port?: number
  username?: string
  remote_dir?: string
  auth?: 'password' | 'key'
  share?: string
  path?: string
  domain?: string | null
  require_encryption?: boolean
  password_set?: boolean
  private_key_set?: boolean
  passphrase_set?: boolean
  host_key_pinned?: boolean
  host_key_fingerprint?: string | null
  last_tested?: string | null
  test_status?: 'ok' | 'failed' | null
  test_error?: string | null
}

export interface RemoteTestResult {
  ok: boolean
  error: string | null
  needs_host_key_confirmation: boolean
  host_key: string | null
  host_key_fingerprint: string | null
}
