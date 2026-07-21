import { useState, useRef, useEffect } from 'react'
import { mfaApi } from '@/lib/apiClient'
import { useAuthStore } from '@/stores/authStore'

interface Props {
  challengeToken: string
  onSuccess: () => void
}

export function MFAVerifyModal({ challengeToken, onSuccess }: Props) {
  const [code, setCode] = useState('')
  const [useBackup, setUseBackup] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [shake, setShake] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const setAuth = useAuthStore((s) => s.setAuth)

  useEffect(() => {
    inputRef.current?.focus()
  }, [useBackup])

  const handleVerify = async () => {
    if (!code.trim()) return
    setLoading(true)
    setError('')
    try {
      const resp = await mfaApi.verify(challengeToken, code.trim())
      const { access_token, user } = resp.data.data
      setAuth(user, access_token)
      onSuccess()
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { error?: { message?: string } } } })
          .response?.data?.error?.message ?? 'Invalid code. Please try again.'
      setError(msg)
      setShake(true)
      setTimeout(() => setShake(false), 500)
      setCode('')
      inputRef.current?.focus()
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 50,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }}>
      <div style={{
        position: 'absolute', inset: 0,
        backdropFilter: 'blur(4px)',
        background: 'rgba(0,0,0,0.6)',
      }} />
      <div
        className={shake ? 'animate-shake' : ''}
        style={{
          position: 'relative', zIndex: 1,
          background: 'var(--bg-surface)',
          border: '1px solid var(--accent)',
          borderRadius: 12,
          padding: 28,
          width: 340,
          boxShadow: 'var(--shadow-accent)',
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 8 }}>
            <img src="/icons/locked_with_key_color.svg" width={28} height={28} alt="" aria-hidden="true" />
          </div>
          <div style={{ fontWeight: 700, fontSize: 16, color: 'var(--text-primary)' }}>
            Two-Factor Authentication
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
            {useBackup
              ? 'Enter one of your backup codes'
              : 'Enter the 6-digit code from your authenticator app'}
          </div>
        </div>

        <input
          ref={inputRef}
          className="form-input"
          type={useBackup ? 'text' : 'number'}
          inputMode="numeric"
          placeholder={useBackup ? 'xxxx-xxxx' : '000000'}
          value={code}
          onChange={(e) => setCode(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleVerify()}
          style={{ textAlign: 'center', letterSpacing: useBackup ? 2 : 8, fontSize: 18, marginBottom: 12 }}
          maxLength={useBackup ? 9 : 6}
        />

        {error && (
          <div style={{ color: 'var(--red)', fontSize: 12, textAlign: 'center', marginBottom: 8 }}>
            {error}
          </div>
        )}

        <button
          className="btn btn-accent"
          style={{ width: '100%' }}
          onClick={handleVerify}
          disabled={loading || code.length < (useBackup ? 9 : 6)}
        >
          {loading ? 'Verifying…' : 'Verify'}
        </button>

        <button
          className="btn btn-ghost"
          style={{ width: '100%', marginTop: 8, fontSize: 12 }}
          onClick={() => { setUseBackup((v) => !v); setCode(''); setError('') }}
        >
          {useBackup ? '← Use authenticator code' : 'Use a backup code instead'}
        </button>
      </div>
    </div>
  )
}
