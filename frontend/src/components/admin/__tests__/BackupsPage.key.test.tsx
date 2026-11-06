import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import type { BackupConfig } from '@/types/backup'

let config: BackupConfig
const mutation = { mutate: vi.fn(), mutateAsync: vi.fn(), isPending: false }
vi.mock('@/hooks/useBackup', () => ({
  useBackupConfig: () => ({ data: config }),
  useBackupRecords: () => ({ data: [] }),
  useUpdateBackupConfig: () => mutation,
  useTriggerBackup: () => mutation,
}))

import { BackupsPage } from '../BackupsPage'

function base(over: Partial<BackupConfig> = {}): BackupConfig {
  return {
    id: 'c', enabled: true, schedule: 'daily', retention_days: 90, destination: 'local',
    last_backup_at: null, last_backup_status: null, last_backup_error: null, last_backup_size_bytes: null,
    key_fingerprint: 'ab12cd34ef567890', key_source: 'dedicated', legacy_backup_count: 0,
    ...over,
  }
}

// #149: the dedicated backup key and the backups still on the old key.
describe('BackupsPage encryption key', () => {
  it('shows the key fingerprint', () => {
    config = base()
    render(<BackupsPage />)
    expect(screen.getByText('ab12cd34ef567890')).toBeInTheDocument()
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
