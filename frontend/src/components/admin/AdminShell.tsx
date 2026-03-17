import { type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { useFeatureFlags } from '@/hooks/useFeatureFlags'

type AdminTab = 'team' | 'org' | 'storage' | 'templates' | 'audit' | 'sso'

interface AdminShellProps {
  children: ReactNode
  activeTab: AdminTab
  onTabChange: (tab: AdminTab) => void
}

interface SidebarItem {
  id: AdminTab
  icon: string
  label: string
  premium?: string
}

const SIDEBAR_ITEMS: SidebarItem[] = [
  { id: 'team', icon: '👥', label: 'Team' },
  { id: 'org', icon: '⚙️', label: 'Org Settings' },
  { id: 'storage', icon: '🗄️', label: 'Storage' },
  { id: 'templates', icon: '📋', label: 'Incident Templates' },
  { id: 'audit', icon: '📜', label: 'Audit Log', premium: 'audit_log' },
  { id: 'sso', icon: '🔐', label: 'SSO', premium: 'sso_saml' },
]

export function AdminShell({ children, activeTab, onTabChange }: AdminShellProps) {
  const navigate = useNavigate()
  const { hasFeature } = useFeatureFlags()

  return (
    <div
      style={{
        display: 'flex',
        height: '100vh',
        overflow: 'hidden',
        background: 'var(--bg-base)',
      }}
    >
      {/* Sidebar */}
      <aside
        style={{
          width: 220,
          background: 'var(--bg-surface)',
          borderRight: '1px solid var(--border)',
          display: 'flex',
          flexDirection: 'column',
          flexShrink: 0,
          padding: '16px 0',
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '0 16px 16px',
            borderBottom: '1px solid var(--border)',
            marginBottom: 8,
          }}
        >
          <button
            onClick={() => navigate('/incidents')}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              color: 'var(--text-muted)',
              fontSize: 12,
              fontWeight: 600,
              padding: 0,
              marginBottom: 12,
            }}
            aria-label="Back to incidents"
          >
            ← Back
          </button>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 16 }}>🛡️</span>
            <span
              style={{
                fontSize: 14,
                fontWeight: 800,
                color: 'var(--text-primary)',
                fontFamily: 'Syne, sans-serif',
              }}
            >
              Admin Panel
            </span>
          </div>
        </div>

        {/* Nav items */}
        <nav style={{ flex: 1, padding: '0 8px' }}>
          {SIDEBAR_ITEMS.map((item) => {
            const isActive = activeTab === item.id
            const isPremiumLocked = item.premium ? !hasFeature(item.premium) : false

            return (
              <button
                key={item.id}
                onClick={() => onTabChange(item.id)}
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: '9px 12px',
                  borderRadius: 8,
                  border: 'none',
                  background: isActive ? 'var(--accent-dim)' : 'transparent',
                  color: isActive ? 'var(--accent)' : 'var(--text-secondary)',
                  cursor: 'pointer',
                  fontSize: 13,
                  fontWeight: isActive ? 700 : 500,
                  fontFamily: 'Syne, sans-serif',
                  textAlign: 'left',
                  marginBottom: 2,
                  transition: 'all 0.15s',
                }}
                aria-label={item.label}
              >
                <span style={{ fontSize: 15, flexShrink: 0 }}>{item.icon}</span>
                <span style={{ flex: 1 }}>{item.label}</span>
                {isPremiumLocked && (
                  <span
                    style={{ fontSize: 11, color: 'var(--text-muted)' }}
                    title="Premium feature"
                  >
                    🔒
                  </span>
                )}
              </button>
            )
          })}
        </nav>
      </aside>

      {/* Main content */}
      <main
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        {children}
      </main>
    </div>
  )
}
