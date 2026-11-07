import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import type { BackupConfig, BackupRecord } from '@/types/backup'

let config: BackupConfig
let records: BackupRecord[] = []
const mutation = { mutate: vi.fn(), mutateAsync: vi.fn(), isPending: false }
vi.mock('@/hooks/useBackup', () => ({
  useBackupConfig: () => ({ data: config }),
  useBackupRecords: () => ({ data: records }),
  useUpdateBackupConfig: () => mutation,
  useTriggerBackup: () => mutation,
}))

import { BackupsPage } from '../BackupsPage'

function base(over: Partial<BackupConfig> = {}): BackupConfig {
  return {
    id: 'c', enabled: true, schedule: 'daily', retention_days: 90, destination: 'local',
    last_backup_at: null, last_backup_status: null, last_backup_error: null, last_backup_size_bytes: null,
    key_fingerprint: '0000111122223333', key_source: 'dedicated', legacy_backup_count: 0,
    ...over,
  }
}

// #149: the dedicated backup key and the backups still on the old key.
describe('BackupsPage encryption key', () => {
  it('shows the key fingerprint', () => {
    config = base()
    render(<BackupsPage />)
    expect(screen.getByText('0000111122223333')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('warns when backups still use the SECRET_KEY-derived key', () => {
    config = base({ key_source: 'secret_key_fallback' })
    render(<BackupsPage />)
    expect(screen.getByRole('alert')).toHaveTextContent('No dedicated backup key')
  })

  it('says how many backups need rekeying', () => {
    config = base({ legacy_backup_count: 3 })
    render(<BackupsPage />)
    expect(screen.getByText(/3 backups are encrypted with/)).toBeInTheDocument()
  })
})

// Every destination keeps the local copy, so every successful backup can be downloaded.
describe('BackupsPage backup list', () => {
  it('offers Download for successful backups on any destination, not for failed ones', () => {
    config = base()
    const rec = (id: string, destination: string, status: BackupRecord['status']): BackupRecord => ({
      id, filename: `irdoc_backup_${id}.enc`, size_bytes: 10, destination, status, error: null,
      key_fingerprint: null, created_at: '2026-11-07T00:00:00Z',
    })
    records = [rec('1', 'local', 'success'), rec('2', 'sftp', 'success'), rec('3', 'smb', 'success'),
      rec('4', 'cloud', 'success'), rec('5', 'sftp', 'failed')]
    render(<BackupsPage />)
    expect(screen.getAllByRole('button', { name: 'Download' })).toHaveLength(4)
    records = []
  })
})
