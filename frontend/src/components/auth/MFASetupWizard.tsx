import { useState } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import { mfaApi } from '@/lib/apiClient'
import { useAuthStore } from '@/stores/authStore'
import type { User } from '@/types/user'

interface Props {
  setupToken: string  // mfa_setup JWT for forced enrollment; empty string for voluntary (uses access token)
  asModal?: boolean   // true = modal overlay; false (default) = full-page gate
  onSuccess?: () => void
}

export function MFASetupWizard({ setupToken, asModal = false, onSuccess }: Props) {
  const [step, setStep] = useState(1)
  const [secretUri, setSecretUri] = useState('')
  const [code, setCode] = useState('')
  const [codeError, setCodeError] = useState('')
  const [backupCodes, setBackupCodes] = useState<string[]>([])
  const [realTokens, setRealTokens] = useState<{ access_token: string; user: User } | null>(null)
  const [savedConfirmed, setSavedConfirmed] = useState(false)
  const [loading, setLoading] = useState(false)
  const setAuth = useAuthStore((s) => s.setAuth)

  const handleHaveApp = async () => {
    setLoading(true)
    try {
      const resp = setupToken
        ? await mfaApi.getSetup(setupToken)
        : await mfaApi.getSetupWithAccessToken()
      setSecretUri(resp.data.data.secret_uri)
      setStep(2)
    } finally {
      setLoading(false)
    }
  }

  const handleVerifyCode = async () => {
    setCodeError('')
    setLoading(true)
    try {
      const resp = setupToken
        ? await mfaApi.completeSetup(setupToken, code.trim())
        : await mfaApi.completeSetupWithAccessToken(code.trim())
      const { access_token, backup_codes, user } = resp.data.data
      setBackupCodes(backup_codes)
      setRealTokens({ access_token, user })
      setStep(4)
    } catch (err: unknown) {
      setCodeError(
        (err as { response?: { data?: { error?: { message?: string } } } })
          .response?.data?.error?.message ?? 'Invalid code — check your app and try again.',
      )
    } finally {
      setLoading(false)
    }
  }

  const handleEnterApp = () => {
    if (!realTokens) return
    setAuth(realTokens.user, realTokens.access_token)
    onSuccess?.()
  }

  const handleCopyAll = () => {
    navigator.clipboard.writeText(backupCodes.join('\n'))
  }

  const handleDownload = () => {
    const blob = new Blob([backupCodes.join('\n')], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'irdoc-backup-codes.txt'
    a.click()
    URL.revokeObjectURL(url)
  }

  const manualKey = secretUri
    ? new URLSearchParams(secretUri.split('?')[1]).get('secret') ?? ''
    : ''

  const progressBar = (
    <div style={{ display: 'flex', gap: 6, marginBottom: 24, alignItems: 'center' }}>
      {[1, 2, 3, 4].map((i) => (
        <div
          key={i}
          style={{
            height: 3, flex: 1,
            background: i <= step ? 'var(--accent)' : 'var(--border)',
            borderRadius: 2,
            transition: 'background 0.3s',
          }}
        />
      ))}
      <div style={{ color: 'var(--text-muted)', fontSize: 11, whiteSpace: 'nowrap' }}>
        {step} of 4
      </div>
    </div>
  )

  const content = (
    <div style={{ width: '100%', maxWidth: 440 }}>
      {progressBar}

      {step === 1 && (
        <div style={{ textAlign: 'center' }}>
          <div style={{ marginBottom: 12 }}><img src="/icons/mobile_phone_color.svg" width={32} height={32} alt="" aria-hidden="true" /></div>
          <div style={{ fontWeight: 700, fontSize: 17, marginBottom: 6, color: 'var(--text-primary)' }}>
            Install an authenticator app
          </div>
          <div style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 20 }}>
            You'll need an authenticator app to set up two-factor authentication.
          </div>
          <div style={{ display: 'flex', gap: 10, justifyContent: 'center', flexWrap: 'wrap', marginBottom: 24 }}>
            {['Google Authenticator', 'Authy', 'Microsoft Authenticator', '1Password'].map((app) => (
              <div key={app} style={{
                background: 'var(--bg-elevated)', border: '1px solid var(--border)',
                borderRadius: 8, padding: '8px 14px', fontSize: 12, color: 'var(--text-secondary)',
              }}>
                {app}
              </div>
            ))}
          </div>
          <button className="btn btn-accent" style={{ width: '100%' }} onClick={handleHaveApp} disabled={loading}>
            {loading ? 'Loading…' : "I have an app →"}
          </button>
        </div>
      )}

      {step === 2 && secretUri && (
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontWeight: 700, fontSize: 17, marginBottom: 6, color: 'var(--text-primary)' }}>
            Scan this QR code
          </div>
          <div style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 20 }}>
            Open your authenticator app and scan the code below
          </div>
          <div style={{ background: 'white', display: 'inline-block', padding: 12, borderRadius: 8, marginBottom: 16 }}>
            <QRCodeSVG value={secretUri} size={160} />
          </div>
          <div style={{
            background: 'var(--bg-elevated)', border: '1px solid var(--border)',
            borderRadius: 8, padding: '10px 16px', marginBottom: 20,
          }}>
            <div style={{ color: 'var(--text-muted)', fontSize: 11, marginBottom: 4 }}>
              Can't scan? Enter this key manually:
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--accent)', letterSpacing: 2 }}>
              {manualKey.match(/.{1,4}/g)?.join(' ')}
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn btn-ghost" style={{ flex: 1 }} onClick={() => setStep(1)}>← Back</button>
            <button className="btn btn-accent" style={{ flex: 2 }} onClick={() => setStep(3)}>
              I've scanned it →
            </button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontWeight: 700, fontSize: 17, marginBottom: 6, color: 'var(--text-primary)' }}>
            Enter the 6-digit code
          </div>
          <div style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 20 }}>
            Open your authenticator app and enter the current code to confirm setup
          </div>
          <input
            className="form-input"
            type="number"
            inputMode="numeric"
            placeholder="000000"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleVerifyCode()}
            maxLength={6}
            style={{ textAlign: 'center', letterSpacing: 8, fontSize: 22, marginBottom: 8 }}
            autoFocus
          />
          {codeError && (
            <div style={{ color: 'var(--red)', fontSize: 12, marginBottom: 8 }}>{codeError}</div>
          )}
          <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
            <button className="btn btn-ghost" style={{ flex: 1 }} onClick={() => setStep(2)}>← Back</button>
            <button
              className="btn btn-accent"
              style={{ flex: 2 }}
              onClick={handleVerifyCode}
              disabled={loading || code.length < 6}
            >
              {loading ? 'Verifying…' : 'Confirm →'}
            </button>
          </div>
        </div>
      )}

      {step === 4 && (
        <div>
          <div style={{ fontWeight: 700, fontSize: 17, marginBottom: 6, textAlign: 'center', color: 'var(--text-primary)' }}>
            Save your backup codes
          </div>
          <div style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 16, textAlign: 'center' }}>
            Store these somewhere safe. Each code can only be used once if you lose your authenticator.
          </div>
          <div style={{
            display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6,
            background: 'var(--bg-elevated)', border: '1px solid var(--border)',
            borderRadius: 8, padding: 16, marginBottom: 12,
          }}>
            {backupCodes.map((c) => (
              <div key={c} style={{
                fontFamily: 'var(--font-mono)', fontSize: 13,
                color: 'var(--text-secondary)', padding: '4px 8px',
                background: 'var(--bg-surface)', borderRadius: 4,
              }}>
                {c}
              </div>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
            <button className="btn btn-ghost btn-sm" style={{ flex: 1 }} onClick={handleCopyAll}>Copy all</button>
            <button className="btn btn-ghost btn-sm" style={{ flex: 1 }} onClick={handleDownload}>Download .txt</button>
          </div>
          <label style={{ display: 'flex', gap: 10, alignItems: 'flex-start', cursor: 'pointer', marginBottom: 16 }}>
            <input
              type="checkbox"
              checked={savedConfirmed}
              onChange={(e) => setSavedConfirmed(e.target.checked)}
              style={{ marginTop: 2 }}
            />
            <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
              I've saved these codes somewhere safe
            </span>
          </label>
          <button
            className="btn btn-accent"
            style={{ width: '100%' }}
            onClick={handleEnterApp}
            disabled={!savedConfirmed}
          >
            Enable Two-Factor Authentication ✓
          </button>
        </div>
      )}
    </div>
  )

  if (asModal) {
    return (
      <div style={{
        position: 'fixed', inset: 0, zIndex: 50,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <div style={{
          position: 'absolute', inset: 0,
          backdropFilter: 'blur(4px)', background: 'rgba(0,0,0,0.6)',
        }} />
        <div style={{
          position: 'relative', zIndex: 1,
          background: 'var(--bg-surface)', border: '1px solid var(--border)',
          borderRadius: 12, padding: 32, width: '90%', maxWidth: 480,
          maxHeight: '90vh', overflowY: 'auto',
        }}>
          {content}
        </div>
      </div>
    )
  }

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'var(--bg-base)',
    }}>
      <div style={{
        background: 'var(--bg-surface)', border: '1px solid var(--border)',
        borderRadius: 12, padding: 40, width: '90%', maxWidth: 480,
      }}>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <div style={{
            width: 44, height: 44,
            background: 'linear-gradient(135deg, var(--accent), #ea580c)',
            borderRadius: 10, margin: '0 auto 10px',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 22,
          }}><img src="/icons/shield_color.svg" width={32} height={32} alt="" aria-hidden="true" /></div>
          <div style={{ fontSize: 22, fontWeight: 800, color: 'var(--text-primary)' }}>IRDoc</div>
          <div style={{ color: 'var(--text-muted)', fontSize: 12, marginTop: 2 }}>
            Two-factor authentication setup required
          </div>
        </div>
        {content}
      </div>
    </div>
  )
}
