import { useNavigate, useLocation } from 'react-router-dom'
import { useThemeStore } from '@/stores/themeStore'
import { useLogout } from '@/hooks/useAuth'
import { useAuthStore } from '@/stores/authStore'
import { getInitials } from '@/lib/utils'

interface NavItem {
  icon: string
  label: string
  path: string
  external?: boolean
}

const NAV_ITEMS: NavItem[] = [
  { icon: '⚡', label: 'Incidents',    path: '/incidents' },
  { icon: '🔗', label: 'Integrations', path: '/integrations' },
  { icon: '⚙',  label: 'Settings',    path: '/settings' },
]

function NavButton({
  icon,
  label,
  active,
  onClick,
}: {
  icon: string
  label: string
  active: boolean
  onClick: () => void
}) {
  return (
    <button
      className="nav-btn"
      style={{
        width: 42,
        height: 42,
        borderRadius: 10,
        border: 'none',
        background: active ? 'var(--accent-dim)' : 'transparent',
        color: active ? 'var(--accent)' : 'var(--text-muted)',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: 18,
        transition: 'all 0.15s',
        position: 'relative',
      }}
      onClick={onClick}
      aria-label={label}
      title={label}
    >
      {icon}
      <span
        style={{
          position: 'absolute',
          left: 'calc(100% + 10px)',
          background: 'var(--bg-card)',
          border: '1px solid var(--border)',
          color: 'var(--text-primary)',
          fontSize: 12,
          padding: '4px 10px',
          borderRadius: 6,
          whiteSpace: 'nowrap',
          pointerEvents: 'none',
          zIndex: 999,
          fontFamily: 'Syne, sans-serif',
          fontWeight: 600,
        }}
        className="nav-tooltip opacity-0 group-hover:opacity-100 transition-opacity"
      >
        {label}
      </span>
    </button>
  )
}

export function LeftNav() {
  const navigate = useNavigate()
  const location = useLocation()
  const { toggle } = useThemeStore()
  const logout = useLogout()
  const user = useAuthStore((s) => s.user)

  return (
    <nav
      style={{
        width: 60,
        background: 'var(--bg-surface)',
        borderRight: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '16px 0',
        gap: 4,
        flexShrink: 0,
        zIndex: 100,
      }}
    >
      {/* Logo */}
      <div
        style={{
          width: 36,
          height: 36,
          background: 'var(--accent)',
          borderRadius: 10,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontWeight: 800,
          fontSize: 12,
          color: '#fff',
          marginBottom: 16,
          letterSpacing: '-0.5px',
          cursor: 'pointer',
          flexShrink: 0,
        }}
        onClick={() => navigate('/incidents')}
        title="IRDoc"
      >
        IR
      </div>

      {/* Nav Items */}
      {NAV_ITEMS.map((item) => (
        <NavButton
          key={item.path}
          icon={item.icon}
          label={item.label}
          active={location.pathname.startsWith(item.path)}
          onClick={() => navigate(item.path)}
        />
      ))}

      {/* Admin nav item — only visible to admins */}
      {user?.role === 'admin' && (
        <NavButton
          icon="🛡️"
          label="Admin"
          active={location.pathname.startsWith('/admin')}
          onClick={() => navigate('/admin')}
        />
      )}

      <div style={{ flex: 1 }} />

      {/* Theme toggle */}
      <NavButton
        icon="◑"
        label="Toggle theme"
        active={false}
        onClick={toggle}
      />

      {/* User avatar */}
      <button
        onClick={() => navigate('/settings')}
        aria-label="Profile"
        title={user?.full_name ?? 'Profile'}
        style={{
          width: 32,
          height: 32,
          borderRadius: '50%',
          background: 'linear-gradient(135deg, var(--accent), var(--purple))',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 12,
          fontWeight: 800,
          color: '#fff',
          border: 'none',
          cursor: 'pointer',
          marginTop: 4,
          flexShrink: 0,
        }}
      >
        {user ? getInitials(user.full_name) : '?'}
      </button>

      {/* Logout */}
      <NavButton
        icon="→"
        label="Sign out"
        active={false}
        onClick={() => logout.mutate()}
      />
    </nav>
  )
}
