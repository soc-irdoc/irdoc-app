import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useLogin } from '@/hooks/useAuth'
import { useAuthStore } from '@/stores/authStore'
import { Button } from '@/components/common/Button'
import apiClient from '@/lib/apiClient'

export function LoginPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const login = useLogin()
  const user = useAuthStore((s) => s.user)

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const sessionExpired = searchParams.get('reason') === 'session_expired'
  const [error, setError] = useState(sessionExpired ? 'Your session expired. Please log in again.' : '')

  // Check if first-run setup is needed
  const [needsSetup, setNeedsSetup] = useState(false)
  const [setupName, setSetupName] = useState('')
  const [setupEmail, setSetupEmail] = useState('admin@localhost')
  const [setupPw, setSetupPw] = useState('')
  const [setupLoading, setSetupLoading] = useState(false)

  useEffect(() => {
    if (user) navigate('/incidents', { replace: true })
  }, [user, navigate])

  useEffect(() => {
    apiClient.get<{ data: { setup_complete: boolean } }>('/auth/setup-status')
      .then((res) => {
        if (!res.data.data.setup_complete) setNeedsSetup(true)
      })
      .catch(() => {})
  }, [])

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    try {
      await login.mutateAsync({ email, password })
      navigate('/incidents', { replace: true })
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } }
      setError(axiosErr.response?.data?.detail ?? 'Invalid credentials')
    }
  }

  async function handleSetup(e: React.FormEvent) {
    e.preventDefault()
    setSetupLoading(true)
    try {
      await apiClient.post('/auth/setup', {
        full_name: setupName,
        email: setupEmail,
        password: setupPw,
      })
      setNeedsSetup(false)
      setEmail(setupEmail)
      setPassword(setupPw)
    } catch {
      setError('Setup failed. Please try again.')
    } finally {
      setSetupLoading(false)
    }
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        background: 'var(--bg-base)',
        backgroundImage: `
          radial-gradient(ellipse at 60% 0%, rgba(249,115,22,0.06) 0%, transparent 55%),
          linear-gradient(var(--border-subtle) 1px, transparent 1px),
          linear-gradient(90deg, var(--border-subtle) 1px, transparent 1px)
        `,
        backgroundSize: 'auto, 40px 40px, 40px 40px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
      }}
    >
      <div className="animate-enter-up" style={{ width: '100%', maxWidth: 400 }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: 40 }}>
          <div
            style={{
              width: 56,
              height: 56,
              background: 'linear-gradient(135deg, var(--accent), rgba(249,115,22,0.7))',
              borderRadius: 16,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 26,
              margin: '0 auto 16px',
              boxShadow: '0 0 24px rgba(249,115,22,0.25)',
            }}
          >
            🛡
          </div>
          <h1
            style={{
              fontFamily: 'Syne, sans-serif',
              fontSize: 32,
              fontWeight: 800,
              color: 'var(--text-primary)',
              letterSpacing: '-0.03em',
              marginBottom: 6,
            }}
          >
            IRDoc
          </h1>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic', marginBottom: 6 }}>
            Incident Response, Documented.
          </p>
          <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
            {needsSetup ? 'Create your admin account to get started' : 'Sign in to your workspace'}
          </p>
        </div>

        <div
          style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            borderRadius: 16,
            padding: 32,
            boxShadow: 'var(--shadow)',
          }}
        >
          {needsSetup ? (
            /* First-run setup */
            <form onSubmit={handleSetup} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <h2 style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 4 }}>
                Initial Setup
              </h2>
              <input
                type="text"
                className="form-input"
                placeholder="Full name"
                value={setupName}
                onChange={(e) => setSetupName(e.target.value)}
                required
                autoFocus
              />
              <input
                type="email"
                className="form-input"
                placeholder="Admin email"
                value={setupEmail}
                onChange={(e) => setSetupEmail(e.target.value)}
                required
              />
              <input
                type="password"
                className="form-input"
                placeholder="Password (min 12 chars)"
                value={setupPw}
                onChange={(e) => setSetupPw(e.target.value)}
                minLength={12}
                required
              />
              {error && (
                <p style={{ fontSize: 13, color: 'var(--red)' }}>{error}</p>
              )}
              <Button type="submit" variant="accent" loading={setupLoading} style={{ width: '100%' }}>
                Create Account
              </Button>
            </form>
          ) : (
            /* Login form */
            <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div>
                <label
                  style={{
                    fontSize: 11,
                    fontWeight: 600,
                    color: 'var(--text-muted)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px',
                    marginBottom: 6,
                    display: 'block',
                  }}
                >
                  Email
                </label>
                <input
                  type="email"
                  className="form-input"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoFocus
                />
              </div>
              <div>
                <label
                  style={{
                    fontSize: 11,
                    fontWeight: 600,
                    color: 'var(--text-muted)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px',
                    marginBottom: 6,
                    display: 'block',
                  }}
                >
                  Password
                </label>
                <input
                  type="password"
                  className="form-input"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>
              {error && (
                <p style={{ fontSize: 13, color: 'var(--red)' }}>{error}</p>
              )}
              <Button
                type="submit"
                variant="accent"
                loading={login.isPending}
                style={{ width: '100%', justifyContent: 'center', marginTop: 4 }}
              >
                Sign In
              </Button>

              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  margin: '8px 0',
                }}
              >
                <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
                <span style={{ fontSize: 11, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                  or
                </span>
                <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
              </div>

              <button
                type="button"
                className="btn btn-ghost"
                style={{ width: '100%', justifyContent: 'center' }}
                onClick={async () => {
                  try {
                    const res = await apiClient.get<{ data: { redirect_url: string } }>('/auth/saml/login')
                    window.location.href = res.data.data.redirect_url
                  } catch {
                    setError('SSO is not configured for this organisation.')
                  }
                }}
              >
                🔐 Sign in with SSO
              </button>
            </form>
          )}
        </div>

        <p
          style={{
            textAlign: 'center',
            marginTop: 24,
            fontSize: 12,
            color: 'var(--text-muted)',
          }}
        >
          IRDoc — Incident Response Documentation Platform
        </p>
      </div>
    </div>
  )
}
