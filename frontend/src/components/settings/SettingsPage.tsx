import { useState } from 'react'
import { useAuthStore } from '@/stores/authStore'
import { useThemeStore } from '@/stores/themeStore'
import { useChangePassword } from '@/hooks/useAuth'
import { APIKeysSection } from './APIKeysSection'
import { ToggleSwitch } from '@/components/common/ToggleSwitch'
import { Button } from '@/components/common/Button'
import { useUIStore } from '@/stores/uiStore'
import { getInitials } from '@/lib/utils'
import { mfaApi } from '@/lib/apiClient'
import { MFASetupWizard } from '@/components/auth/MFASetupWizard'
import { useVersion } from '@/hooks/useVersion'

function SettingsSection({
  icon,
  title,
  children,
}: {
  icon: string
  title: string
  children: React.ReactNode
}) {
  return (
    <div
      style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderRadius: 12,
        overflow: 'hidden',
        marginBottom: 16,
      }}
    >
      <div
        style={{
          padding: '14px 20px',
          borderBottom: '1px solid var(--border)',
          fontSize: 13,
          fontWeight: 700,
          color: 'var(--text-primary)',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}
      >
        <img src={`/icons/${icon}`} width={20} height={20} alt="" aria-hidden="true" /> {title}
      </div>
      {children}
    </div>
  )
}

function SettingsRow({
  title,
  description,
  children,
}: {
  title: string
  description?: string
  children: React.ReactNode
}) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        padding: '14px 20px',
        borderBottom: '1px solid var(--border-subtle)',
        gap: 16,
      }}
    >
      <div style={{ flex: 1 }}>
        <h4 style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{title}</h4>
        {description && (
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>{description}</p>
        )}
      </div>
      {children}
    </div>
  )
}

export function SettingsPage() {
  const addToast = useUIStore((s) => s.addToast)
  const user = useAuthStore((s) => s.user)
  const setUser = useAuthStore((s) => s.setUser)
  const { theme, toggle } = useThemeStore()
  const changePassword = useChangePassword()
  const { version, latestVersion, updateAvailable } = useVersion()

  const [currentPw, setCurrentPw] = useState('')
  const [newPw, setNewPw] = useState('')
  const [confirmPw, setConfirmPw] = useState('')
  const [showPwForm, setShowPwForm] = useState(false)

  // MFA state
  const [showSetupWizard, setShowSetupWizard] = useState(false)
  const [showDisableConfirm, setShowDisableConfirm] = useState(false)
  const [showNewCodes, setShowNewCodes] = useState(false)
  const [newBackupCodes, setNewBackupCodes] = useState<string[]>([])
  const [mfaLoading, setMfaLoading] = useState(false)

  async function handleRegenerateCodes() {
    setMfaLoading(true)
    try {
      const res = await mfaApi.regenerateBackupCodes()
      setNewBackupCodes(res.data.data.codes)
      setShowNewCodes(true)
    } catch {
      addToast('Failed to regenerate backup codes', 'error')
    } finally {
      setMfaLoading(false)
    }
  }

  async function handleDisableMFA() {
    setMfaLoading(true)
    try {
      await mfaApi.disable()
      if (user) setUser({ ...user, mfa_enabled: false, backup_codes_remaining: 0 })
      setShowDisableConfirm(false)
      addToast('Two-factor authentication removed', 'success')
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } }
      addToast(axiosErr.response?.data?.detail ?? 'Failed to disable MFA', 'error')
    } finally {
      setMfaLoading(false)
    }
  }

  async function handleChangePw(e: React.FormEvent) {
    e.preventDefault()
    if (newPw !== confirmPw) {
      addToast('Passwords do not match', 'error')
      return
    }
    try {
      await changePassword.mutateAsync({ current_password: currentPw, new_password: newPw })
      addToast('Password changed', 'success')
      setShowPwForm(false)
      setCurrentPw('')
      setNewPw('')
      setConfirmPw('')
    } catch {
      addToast('Failed to change password', 'error')
    }
  }

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: 24 }}>
      <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'Syne, sans-serif', marginBottom: 20 }}>
        Settings
      </div>
      {/* Security */}
      <SettingsSection icon="locked_with_key_color.svg" title="Two-Factor Authentication">
        {user?.mfa_enabled ? (
          <>
            <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', gap: 12 }}>
              <span className="chip chip-green" style={{ fontSize: 11 }}>Enabled ✓</span>
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                {user.backup_codes_remaining} backup code{user.backup_codes_remaining !== 1 ? 's' : ''} remaining
              </span>
            </div>
            <div style={{ padding: '14px 20px', display: 'flex', gap: 8 }}>
              <Button variant="ghost" size="sm" onClick={handleRegenerateCodes} loading={mfaLoading}>
                Regenerate backup codes
              </Button>
              <Button variant="danger" size="sm" onClick={() => setShowDisableConfirm(true)}>
                Remove MFA
              </Button>
            </div>
          </>
        ) : (
          <div style={{ padding: '16px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16 }}>
            <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
              Add an extra layer of security to your account using an authenticator app.
            </p>
            <Button variant="accent" size="sm" onClick={() => setShowSetupWizard(true)} style={{ flexShrink: 0 }}>
              Enable 2FA
            </Button>
          </div>
        )}
      </SettingsSection>

      {/* Profile */}
      <SettingsSection icon="bust_in_silhouette_color.svg" title="Profile">
        <div style={{ padding: '20px', display: 'flex', alignItems: 'center', gap: 20 }}>
          <div
            style={{
              width: 72,
              height: 72,
              borderRadius: '50%',
              background: 'linear-gradient(135deg, var(--accent), var(--purple))',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 28,
              fontWeight: 800,
              color: '#fff',
              flexShrink: 0,
            }}
          >
            {user ? getInitials(user.full_name) : '?'}
          </div>
          <div>
            <p style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)' }}>
              {user?.full_name}
            </p>
            <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>{user?.email}</p>
            <p
              className="chip chip-blue"
              style={{ marginTop: 6, display: 'inline-flex', fontSize: 10 }}
            >
              {user?.role.replace('_', ' ')}
            </p>
          </div>
        </div>

        {/* Change Password */}
        <SettingsRow
          title="Password"
          description="Change your account password"
        >
          <Button variant="ghost" size="sm" onClick={() => setShowPwForm(!showPwForm)}>
            {showPwForm ? 'Cancel' : 'Change'}
          </Button>
        </SettingsRow>

        {showPwForm && (
          <form onSubmit={handleChangePw} style={{ padding: '0 20px 20px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxWidth: 360 }}>
              <input
                type="password"
                className="form-input"
                placeholder="Current password"
                value={currentPw}
                onChange={(e) => setCurrentPw(e.target.value)}
                required
              />
              <input
                type="password"
                className="form-input"
                placeholder="New password (min 8 chars)"
                value={newPw}
                onChange={(e) => setNewPw(e.target.value)}
                minLength={8}
                required
              />
              <input
                type="password"
                className="form-input"
                placeholder="Confirm new password"
                value={confirmPw}
                onChange={(e) => setConfirmPw(e.target.value)}
                required
              />
              <Button
                type="submit"
                variant="accent"
                size="sm"
                loading={changePassword.isPending}
                style={{ alignSelf: 'flex-start' }}
              >
                Update Password
              </Button>
            </div>
          </form>
        )}
      </SettingsSection>

      {/* Appearance */}
      <SettingsSection icon="artist_palette_color.svg" title="Appearance">
        <SettingsRow
          title="Theme"
          description="Switch between dark and light mode"
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              {theme === 'dark'
                ? <><img src="/icons/crescent_moon_color.svg" width={14} height={14} alt="" aria-hidden="true" style={{ verticalAlign: 'middle', marginRight: 4 }} />Dark</>
                : <><img src="/icons/sun_color.svg" width={14} height={14} alt="" aria-hidden="true" style={{ verticalAlign: 'middle', marginRight: 4 }} />Light</>
              }
            </span>
            <ToggleSwitch
              checked={theme === 'light'}
              onChange={toggle}
              ariaLabel="Toggle theme"
            />
          </div>
        </SettingsRow>
      </SettingsSection>

      {/* API Keys */}
      {user?.role === 'admin' && <APIKeysSection />}

      {/* About */}
      <SettingsSection icon="information_color.svg" title="About IRDoc">
        <div style={{ padding: '16px 20px', fontSize: 13, color: 'var(--text-muted)' }}>
          <p>
            <strong style={{ color: 'var(--text-primary)' }}>IRDoc</strong> — Open-Core Incident
            Response Documentation Platform
          </p>
          <p style={{ marginTop: 8 }}>
            Licensed under{' '}
            <span style={{ color: 'var(--accent)' }}>AGPL-3.0</span>.
          </p>
          {version && (
            <p style={{ marginTop: 8 }}>
              <a
                href="https://github.com/soc-irdoc/irdoc-app/releases"
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: 'var(--accent)', textDecoration: 'none' }}
              >
                v{version}
              </a>
              {updateAvailable && (
                <a
                  href="https://github.com/soc-irdoc/irdoc-app/releases"
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ display: 'block', marginTop: 4, color: 'var(--yellow)', textDecoration: 'none' }}
                >
                  New version available: v{latestVersion}
                </a>
              )}
            </p>
          )}
        </div>
      </SettingsSection>

      {/* MFA setup wizard (voluntary) */}
      {showSetupWizard && (
        <MFASetupWizard
          setupToken=""
          asModal
          onSuccess={() => {
            setShowSetupWizard(false)
            if (user) setUser({ ...user, mfa_enabled: true })
          }}
        />
      )}

      {/* Disable MFA confirm */}
      {showDisableConfirm && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 50, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,0.6)' }}>
          <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 12, padding: 28, maxWidth: 360, width: '90%' }}>
            <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 8, color: 'var(--text-primary)' }}>Remove two-factor authentication?</div>
            <p style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 20 }}>Your account will be less secure without a second factor.</p>
            <div style={{ display: 'flex', gap: 8 }}>
              <Button variant="ghost" style={{ flex: 1 }} onClick={() => setShowDisableConfirm(false)}>Cancel</Button>
              <Button variant="danger" style={{ flex: 1 }} loading={mfaLoading} onClick={handleDisableMFA}>Remove MFA</Button>
            </div>
          </div>
        </div>
      )}

      {/* New backup codes display */}
      {showNewCodes && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 50, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,0.6)' }}>
          <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 12, padding: 28, maxWidth: 400, width: '90%' }}>
            <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 8, color: 'var(--text-primary)' }}>New backup codes</div>
            <p style={{ color: 'var(--yellow)', fontSize: 12, marginBottom: 14 }}>⚠ Your old codes are now invalid. Save these somewhere safe.</p>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginBottom: 16 }}>
              {newBackupCodes.map((c) => (
                <div key={c} style={{ fontFamily: 'var(--font-mono)', fontSize: 12, padding: '4px 8px', background: 'var(--bg-elevated)', borderRadius: 4, color: 'var(--text-secondary)' }}>{c}</div>
              ))}
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <Button variant="ghost" size="sm" style={{ flex: 1 }} onClick={() => navigator.clipboard.writeText(newBackupCodes.join('\n')).then(() => addToast('Codes copied', 'success'))}>
                Copy all
              </Button>
              <Button variant="accent" style={{ flex: 1 }} onClick={() => setShowNewCodes(false)}>Done</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
