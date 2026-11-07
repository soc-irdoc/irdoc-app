import { useEffect, useState } from 'react'
import { isAxiosError } from 'axios'
import { useRemoteBackupConfig, useSaveRemoteBackupConfig, useTestRemoteBackupConfig } from '@/hooks/useBackup'
import { Modal } from '@/components/common/Modal'
import { Button } from '@/components/common/Button'
import { useUIStore } from '@/stores/uiStore'
import type { RemoteBackupConfig, RemoteBackupKind, RemoteTestResult, SFTPConfigPayload, SMBConfigPayload } from '@/types/backup'

interface Props {
  kind: RemoteBackupKind
}

const inputStyle: React.CSSProperties = { width: '100%' }
const labelStyle: React.CSSProperties = {
  fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase',
  letterSpacing: '0.5px', marginBottom: 4, display: 'block',
}
const warnStyle: React.CSSProperties = {
  padding: '8px 12px', background: 'var(--yellow-dim)', border: '1px solid var(--yellow)',
  borderRadius: 8, fontSize: 12, color: 'var(--text-primary)',
}

function apiError(err: unknown): string {
  if (isAxiosError(err)) {
    const detail = err.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (err.response) return `HTTP ${err.response.status}`
  }
  return err instanceof Error ? err.message : 'Request failed'
}

function Field({ id, label, children }: { id: string; label: string; children: React.ReactNode }) {
  return (
    <div>
      <label htmlFor={id} style={labelStyle}>{label}</label>
      {children}
    </div>
  )
}

function secretPlaceholder(set: boolean | undefined) {
  return set ? 'Saved - leave empty to keep' : ''
}

// SFTP or SMB settings for backups (#151). Secrets are write-only: the API
// only says whether they are set.
export function RemoteBackupDestination({ kind }: Props) {
  const addToast = useUIStore((s) => s.addToast)
  const { data: saved } = useRemoteBackupConfig(kind)
  const save = useSaveRemoteBackupConfig(kind)
  const test = useTestRemoteBackupConfig(kind)

  const [sftp, setSftp] = useState<SFTPConfigPayload>({
    host: '', port: 22, username: '', remote_dir: '.', auth: 'password', password: '', private_key: '', passphrase: '',
  })
  const [smb, setSmb] = useState<SMBConfigPayload>({
    server: '', port: 445, share: '', path: '', username: '', password: '', domain: '', require_encryption: true,
  })
  const [result, setResult] = useState<RemoteTestResult | null>(null)
  const [confirmKey, setConfirmKey] = useState<RemoteTestResult | null>(null)

  useEffect(() => {
    if (!saved?.configured) return
    if (kind === 'sftp') {
      setSftp((s) => ({
        ...s, host: saved.host ?? '', port: saved.port ?? 22, username: saved.username ?? '',
        remote_dir: saved.remote_dir ?? '.', auth: saved.auth ?? 'password',
      }))
    } else {
      setSmb((s) => ({
        ...s, server: saved.server ?? '', port: saved.port ?? 445, share: saved.share ?? '', path: saved.path ?? '',
        username: saved.username ?? '', domain: saved.domain ?? '', require_encryption: saved.require_encryption ?? true,
      }))
    }
  }, [saved, kind])

  const payload = (): SFTPConfigPayload | SMBConfigPayload => (kind === 'sftp' ? sftp : smb)

  async function handleSave(extra: Partial<SFTPConfigPayload> = {}): Promise<RemoteBackupConfig | null> {
    try {
      const out = await save.mutateAsync({ ...payload(), ...extra })
      addToast(`${kind.toUpperCase()} settings saved`, 'success')
      return out
    } catch (err) {
      addToast(`Could not save ${kind.toUpperCase()} settings: ${apiError(err)}`, 'error')
      return null
    }
  }

  async function handleTest(extra: Partial<SFTPConfigPayload> = {}) {
    setResult(null)
    try {
      const r = await test.mutateAsync({ ...payload(), ...extra })
      if (r.needs_host_key_confirmation) setConfirmKey(r)
      else setResult(r)
    } catch (err) {
      setResult({ ok: false, error: apiError(err), needs_host_key_confirmation: false, host_key: null, host_key_fingerprint: null })
    }
  }

  async function handleConfirmKey() {
    if (!confirmKey?.host_key) return
    const hostKey = confirmKey.host_key
    setConfirmKey(null)
    if (await handleSave({ host_key: hostKey })) await handleTest()
  }

  return (
    <div
      data-testid={`remote-${kind}`}
      style={{ marginTop: 12, padding: 14, border: '1px solid var(--border)', borderRadius: 8, display: 'flex', flexDirection: 'column', gap: 12 }}
    >
      {kind === 'sftp' ? (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 100px', gap: 10 }}>
            <Field id="sftp-host" label="Host">
              <input id="sftp-host" className="form-input" style={inputStyle} value={sftp.host}
                onChange={(e) => setSftp({ ...sftp, host: e.target.value })} />
            </Field>
            <Field id="sftp-port" label="Port">
              <input id="sftp-port" type="number" className="form-input" style={inputStyle} value={sftp.port}
                onChange={(e) => setSftp({ ...sftp, port: Number(e.target.value) })} />
            </Field>
          </div>
          <Field id="sftp-user" label="Username">
            <input id="sftp-user" className="form-input" style={inputStyle} value={sftp.username}
              onChange={(e) => setSftp({ ...sftp, username: e.target.value })} />
          </Field>
          <Field id="sftp-dir" label="Remote directory">
            <input id="sftp-dir" className="form-input" style={inputStyle} value={sftp.remote_dir}
              onChange={(e) => setSftp({ ...sftp, remote_dir: e.target.value })} />
          </Field>
          <div style={{ display: 'flex', gap: 16, fontSize: 13 }}>
            {(['password', 'key'] as const).map((a) => (
              <label key={a} style={{ display: 'flex', gap: 6, alignItems: 'center', cursor: 'pointer' }}>
                <input type="radio" name="sftp-auth" checked={sftp.auth === a} onChange={() => setSftp({ ...sftp, auth: a })}
                  style={{ accentColor: 'var(--accent)' }} />
                {a === 'password' ? 'Password' : 'Private key'}
              </label>
            ))}
          </div>
          {sftp.auth === 'password' ? (
            <Field id="sftp-password" label="Password">
              <input id="sftp-password" type="password" className="form-input" style={inputStyle} autoComplete="new-password"
                placeholder={secretPlaceholder(saved?.password_set)} value={sftp.password}
                onChange={(e) => setSftp({ ...sftp, password: e.target.value })} />
            </Field>
          ) : (
            <>
              <Field id="sftp-key" label="Private key (OpenSSH / PEM)">
                <textarea id="sftp-key" className="form-input" rows={4} style={{ ...inputStyle, fontFamily: 'JetBrains Mono, monospace', fontSize: 11 }}
                  placeholder={secretPlaceholder(saved?.private_key_set)} value={sftp.private_key}
                  onChange={(e) => setSftp({ ...sftp, private_key: e.target.value })} />
              </Field>
              <Field id="sftp-passphrase" label="Key passphrase (optional)">
                <input id="sftp-passphrase" type="password" className="form-input" style={inputStyle} autoComplete="new-password"
                  placeholder={secretPlaceholder(saved?.passphrase_set)} value={sftp.passphrase}
                  onChange={(e) => setSftp({ ...sftp, passphrase: e.target.value })} />
              </Field>
            </>
          )}
          <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
            Host key:{' '}
            {saved?.host_key_pinned
              ? <>pinned <code>{saved.host_key_fingerprint}</code></>
              : <span style={{ color: 'var(--yellow)' }}>not pinned yet. Run Test connection to confirm it.</span>}
          </div>
        </>
      ) : (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 100px', gap: 10 }}>
            <Field id="smb-server" label="Server">
              <input id="smb-server" className="form-input" style={inputStyle} value={smb.server}
                onChange={(e) => setSmb({ ...smb, server: e.target.value })} />
            </Field>
            <Field id="smb-port" label="Port">
              <input id="smb-port" type="number" className="form-input" style={inputStyle} value={smb.port}
                onChange={(e) => setSmb({ ...smb, port: Number(e.target.value) })} />
            </Field>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <Field id="smb-share" label="Share">
              <input id="smb-share" className="form-input" style={inputStyle} value={smb.share}
                onChange={(e) => setSmb({ ...smb, share: e.target.value })} />
            </Field>
            <Field id="smb-path" label="Folder in share">
              <input id="smb-path" className="form-input" style={inputStyle} value={smb.path}
                onChange={(e) => setSmb({ ...smb, path: e.target.value })} />
            </Field>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <Field id="smb-user" label="Username">
              <input id="smb-user" className="form-input" style={inputStyle} value={smb.username}
                onChange={(e) => setSmb({ ...smb, username: e.target.value })} />
            </Field>
            <Field id="smb-domain" label="Domain (optional)">
              <input id="smb-domain" className="form-input" style={inputStyle} value={smb.domain}
                onChange={(e) => setSmb({ ...smb, domain: e.target.value })} />
            </Field>
          </div>
          <Field id="smb-password" label="Password">
            <input id="smb-password" type="password" className="form-input" style={inputStyle} autoComplete="new-password"
              placeholder={secretPlaceholder(saved?.password_set)} value={smb.password}
              onChange={(e) => setSmb({ ...smb, password: e.target.value })} />
          </Field>
          <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 13, cursor: 'pointer' }}>
            <input type="checkbox" checked={smb.require_encryption}
              onChange={(e) => setSmb({ ...smb, require_encryption: e.target.checked })} style={{ accentColor: 'var(--accent)' }} />
            Require SMB 3 encryption
          </label>
          {!smb.require_encryption && (
            <div role="alert" style={warnStyle}>
              Encryption is off: credentials are still protected, but the transfer can be read or altered on the
              network. Only turn this off for old NAS devices on a trusted network.
            </div>
          )}
        </>
      )}

      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <Button size="sm" variant="ghost" onClick={() => handleTest()} loading={test.isPending}>Test connection</Button>
        <Button size="sm" variant="accent" onClick={() => handleSave()} loading={save.isPending}>
          Save {kind.toUpperCase()} settings
        </Button>
      </div>
      {result && (
        <div role="status" style={{ fontSize: 12, color: result.ok ? 'var(--green)' : 'var(--red)', whiteSpace: 'pre-wrap' }}>
          {result.ok ? 'Connection OK: a test file was written and deleted.' : `Failed: ${result.error}`}
        </div>
      )}

      {confirmKey && (
        <Modal open onClose={() => setConfirmKey(null)} title="Confirm the server's host key">
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 10 }}>
            Check this fingerprint against the SFTP server (for example <code>ssh-keygen -lf</code> on its host key)
            before trusting it. Backups will refuse any other key.
          </p>
          <p style={{ fontSize: 13, marginBottom: 16 }}><code style={{ wordBreak: 'break-all' }}>{confirmKey.host_key_fingerprint}</code></p>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <Button variant="ghost" onClick={() => setConfirmKey(null)}>Cancel</Button>
            <Button variant="accent" onClick={handleConfirmKey}>Trust this key</Button>
          </div>
        </Modal>
      )}
    </div>
  )
}
