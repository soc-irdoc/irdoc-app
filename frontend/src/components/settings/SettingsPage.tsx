import { useState } from 'react'
import { useAuthStore } from '@/stores/authStore'
import { useThemeStore } from '@/stores/themeStore'
import { useChangePassword } from '@/hooks/useAuth'
import { APIKeysSection } from './APIKeysSection'
import { ToggleSwitch } from '@/components/common/ToggleSwitch'
import { Button } from '@/components/common/Button'
import { useUIStore } from '@/stores/uiStore'
import { getInitials } from '@/lib/utils'

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
        {icon} {title}
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
  const { theme, toggle } = useThemeStore()
  const changePassword = useChangePassword()

  const [currentPw, setCurrentPw] = useState('')
  const [newPw, setNewPw] = useState('')
  const [confirmPw, setConfirmPw] = useState('')
  const [showPwForm, setShowPwForm] = useState(false)

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
      <h2
        style={{
          fontSize: 18,
          fontWeight: 800,
          marginBottom: 24,
          color: 'var(--text-primary)',
        }}
      >
        ⚙ Settings
      </h2>

      {/* Profile */}
      <SettingsSection icon="👤" title="Profile">
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
      <SettingsSection icon="🎨" title="Appearance">
        <SettingsRow
          title="Theme"
          description="Switch between dark and light mode"
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              {theme === 'dark' ? '🌙 Dark' : '☀️ Light'}
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
      <SettingsSection icon="ℹ" title="About IRDoc">
        <div style={{ padding: '16px 20px', fontSize: 13, color: 'var(--text-muted)' }}>
          <p>
            <strong style={{ color: 'var(--text-primary)' }}>IRDoc</strong> — Open-Core Incident
            Response Documentation Platform
          </p>
          <p style={{ marginTop: 8 }}>
            Licensed under{' '}
            <span style={{ color: 'var(--accent)' }}>AGPL-3.0</span> (core features).
            Premium features require a commercial license.
          </p>
        </div>
      </SettingsSection>
    </div>
  )
}
