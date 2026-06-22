import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { Button } from '@/components/common/Button'
import apiClient from '@/lib/apiClient'

interface InviteInfo {
  email: string
  org_name: string
  role: string
}

export default function InviteAcceptPage() {
  const { token } = useParams<{ token: string }>()
  const navigate = useNavigate()
  const { setAuth } = useAuthStore()

  const [inviteInfo, setInviteInfo] = useState<InviteInfo | null>(null)
  const [invalid, setInvalid] = useState(false)
  const [loading, setLoading] = useState(true)

  const [fullName, setFullName] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!token) {
      setInvalid(true)
      setLoading(false)
      return
    }
    apiClient
      .get(`/users/invite/${token}`)
      .then((res) => {
        setInviteInfo(res.data.data)
      })
      .catch(() => {
        setInvalid(true)
      })
      .finally(() => {
        setLoading(false)
      })
  }, [token])

  async function handleAccept(e: React.FormEvent) {
    e.preventDefault()
    if (password.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }
    setSubmitting(true)
    setError('')
    try {
      const res = await apiClient.post(`/users/invite/${token}/accept`, {
        full_name: fullName,
        password,
      })
      const { access_token, user } = res.data.data
      setAuth(user, access_token)
      navigate('/incidents', { replace: true })
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } }
      setError(axiosErr.response?.data?.detail ?? 'Failed to accept invitation. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        background: 'var(--bg-base)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
      }}
    >
      <div style={{ width: '100%', maxWidth: 400 }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: 40 }}>
          <div
            style={{
              width: 52,
              height: 52,
              background: 'var(--accent)',
              borderRadius: 14,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 800,
              fontSize: 18,
              color: '#fff',
              margin: '0 auto 16px',
              letterSpacing: '-0.5px',
            }}
          >
            IR
          </div>
          <h1
            style={{
              fontFamily: 'Syne, sans-serif',
              fontSize: 28,
              fontWeight: 800,
              color: 'var(--text-primary)',
              marginBottom: 8,
            }}
          >
            IRDoc
          </h1>
          <p style={{ fontSize: 14, color: 'var(--text-muted)' }}>Team Invitation</p>
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
          {loading ? (
            <div
              style={{
                textAlign: 'center',
                color: 'var(--text-muted)',
                fontSize: 14,
                padding: '16px 0',
              }}
            >
              Validating invitation…
            </div>
          ) : invalid ? (
            <div style={{ textAlign: 'center' }}>
              <div style={{ marginBottom: 12 }}><img src="/icons/link_color.svg" width={32} height={32} alt="" aria-hidden="true" /></div>
              <h2
                style={{
                  fontSize: 16,
                  fontWeight: 700,
                  color: 'var(--text-primary)',
                  marginBottom: 8,
                }}
              >
                Invalid Invitation
              </h2>
              <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 20 }}>
                This invitation is invalid or has expired. Please ask your administrator for a new
                invite link.
              </p>
              <Link
                to="/login"
                style={{
                  fontSize: 13,
                  color: 'var(--accent)',
                  textDecoration: 'none',
                  fontWeight: 600,
                }}
              >
                ← Back to login
              </Link>
            </div>
          ) : (
            <form onSubmit={handleAccept} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div>
                <h2
                  style={{
                    fontSize: 16,
                    fontWeight: 700,
                    color: 'var(--text-primary)',
                    marginBottom: 4,
                  }}
                >
                  You've been invited to join{' '}
                  <span style={{ color: 'var(--accent)' }}>{inviteInfo?.org_name}</span>
                </h2>
                <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  Complete your account setup below
                </p>
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
                  Email
                </label>
                <input
                  type="email"
                  className="form-input"
                  value={inviteInfo?.email ?? ''}
                  readOnly
                  style={{ opacity: 0.7, cursor: 'not-allowed' }}
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
                  Full Name
                </label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="Your full name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
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
                  placeholder="Min 8 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  minLength={8}
                  required
                />
              </div>

              {error && <p style={{ fontSize: 13, color: 'var(--red)' }}>{error}</p>}

              <Button
                type="submit"
                variant="accent"
                loading={submitting}
                style={{ width: '100%', justifyContent: 'center', marginTop: 4 }}
              >
                Create Account & Join
              </Button>

              <div style={{ textAlign: 'center' }}>
                <Link
                  to="/login"
                  style={{
                    fontSize: 12,
                    color: 'var(--text-muted)',
                    textDecoration: 'none',
                  }}
                >
                  Already have an account? Sign in
                </Link>
              </div>
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
