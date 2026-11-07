import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'

const saveMock = vi.fn()
const testMock = vi.fn()
let saved: Record<string, unknown> = { configured: false }
vi.mock('@/hooks/useBackup', () => ({
  useRemoteBackupConfig: () => ({ data: saved }),
  useSaveRemoteBackupConfig: () => ({ mutateAsync: saveMock, isPending: false }),
  useTestRemoteBackupConfig: () => ({ mutateAsync: testMock, isPending: false }),
}))

import { RemoteBackupDestination } from '../RemoteBackupDestination'

const KEY = 'ssh-ed25519 AAAAC3Nza...'

// #151: SFTP host keys are never trusted without the admin confirming them.
describe('RemoteBackupDestination', () => {
  beforeEach(() => {
    saveMock.mockReset().mockResolvedValue({ configured: true, host_key_pinned: true })
    testMock.mockReset()
    saved = { configured: false }
  })

  it('asks to confirm the SFTP host key, then pins it and tests again', async () => {
    testMock
      .mockResolvedValueOnce({ ok: false, error: null, needs_host_key_confirmation: true, host_key: KEY, host_key_fingerprint: 'SHA256:xyz' })
      .mockResolvedValueOnce({ ok: true, error: null, needs_host_key_confirmation: false, host_key: null, host_key_fingerprint: null })
    render(<RemoteBackupDestination kind="sftp" />)
    fireEvent.change(screen.getByLabelText('Host'), { target: { value: 'nas.local' } })

    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }))
    expect(await screen.findByText('SHA256:xyz')).toBeInTheDocument()
    expect(saveMock).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: 'Trust this key' }))
    await waitFor(() => expect(saveMock).toHaveBeenCalledWith(expect.objectContaining({ host: 'nas.local', host_key: KEY })))
    expect(await screen.findByText(/Connection OK/)).toBeInTheDocument()
  })

  it('shows the test error verbatim', async () => {
    testMock.mockResolvedValue({ ok: false, error: 'Permission denied (publickey)', needs_host_key_confirmation: false, host_key: null, host_key_fingerprint: null })
    render(<RemoteBackupDestination kind="smb" />)
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }))
    expect(await screen.findByText('Failed: Permission denied (publickey)')).toBeInTheDocument()
  })

  it('warns when SMB encryption is turned off', () => {
    render(<RemoteBackupDestination kind="smb" />)
    expect(screen.queryByRole('alert')).toBeNull()
    fireEvent.click(screen.getByLabelText('Require SMB 3 encryption'))
    expect(screen.getByRole('alert')).toHaveTextContent('Encryption is off')
  })

  it('never shows stored secrets, only that they are set', () => {
    saved = { configured: true, kind: 'smb', server: 'nas', share: 'b', password_set: true }
    render(<RemoteBackupDestination kind="smb" />)
    const pw = screen.getByLabelText('Password') as HTMLInputElement
    expect(pw.value).toBe('')
    expect(pw.placeholder).toMatch(/leave empty to keep/)
  })
})
