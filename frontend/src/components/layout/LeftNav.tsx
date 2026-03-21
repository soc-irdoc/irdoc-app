import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useThemeStore } from '@/stores/themeStore'
import { useLogout } from '@/hooks/useAuth'
import { useAuthStore } from '@/stores/authStore'
import { getInitials } from '@/lib/utils'

interface NavItem {
  icon: string
  label: string
  path: string
}

const NAV_ITEMS: NavItem[] = [
  { icon: '⚡', label: 'Incidents', path: '/incidents' },
  { icon: '⚙',  label: 'Settings', path: '/settings' },
]

function NavButton({
  icon,
  label,
  active,
  collapsed,
  onClick,
}: {
  icon: string
  label: string
  active: boolean
  collapsed: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      aria-label={label}
      title={collapsed ? label : undefined}
      style={{
        width: collapsed ? 42 : '100%',
        height: 42,
        borderRadius: 10,
        border: 'none',
        background: active ? 'var(--accent-dim)' : 'transparent',
        color: active ? 'var(--accent)' : 'var(--text-muted)',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: collapsed ? 'center' : 'flex-start',
        gap: 10,
        fontSize: 18,
        padding: collapsed ? 0 : '0 12px',
        transition: 'background 0.15s, color 0.15s',
        position: 'relative',
        flexShrink: 0,
        whiteSpace: 'nowrap',
        overflow: 'hidden',
      }}
    >
      <span style={{ flexShrink: 0, lineHeight: 1 }}>{icon}</span>
      {!collapsed && (
        <span style={{
          fontSize: 13,
          fontFamily: 'Syne, sans-serif',
          fontWeight: 600,
          color: active ? 'var(--accent)' : 'var(--text-secondary)',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
        }}>
          {label}
        </span>
      )}
    </button>
  )
}

export function LeftNav() {
  const navigate = useNavigate()
  const location = useLocation()
  const { toggle } = useThemeStore()
  const logout = useLogout()
  const user = useAuthStore((s) => s.user)

  const [collapsed, setCollapsed] = useState<boolean>(
    () => localStorage.getItem('nav-collapsed') === 'true'
  )

  function toggleCollapsed() {
    const next = !collapsed
    setCollapsed(next)
    localStorage.setItem('nav-collapsed', String(next))
  }

  const navWidth = collapsed ? 60 : 210

  return (
    <nav
      style={{
        width: navWidth,
        minWidth: navWidth,
        background: 'var(--bg-surface)',
        borderRight: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: collapsed ? 'center' : 'stretch',
        padding: collapsed ? '16px 0' : '16px 10px',
        gap: 4,
        flexShrink: 0,
        zIndex: 100,
        transition: 'width 0.2s ease, min-width 0.2s ease, padding 0.2s ease',
        overflow: 'hidden',
      }}
    >
      {/* Logo row */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: collapsed ? 'center' : 'flex-start',
        gap: 10,
        flexShrink: 0,
        padding: collapsed ? 0 : '0 2px',
      }}>
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
            letterSpacing: '-0.5px',
            cursor: 'pointer',
            flexShrink: 0,
          }}
          onClick={() => navigate('/incidents')}
          title="IRDoc"
        >
          IR
        </div>

        {!collapsed && (
          <span style={{
            fontFamily: 'Syne, sans-serif',
            fontWeight: 800,
            fontSize: 15,
            color: 'var(--text-primary)',
            letterSpacing: '-0.3px',
          }}>
            IRDoc
          </span>
        )}
      </div>

      {/* Collapse toggle — small icon button, same size in both states */}
      <button
        onClick={toggleCollapsed}
        aria-label={collapsed ? 'Expand navigation' : 'Collapse navigation'}
        title={collapsed ? 'Expand navigation' : 'Collapse navigation'}
        style={{
          width: 28,
          height: 28,
          borderRadius: 8,
          border: '1px solid var(--border)',
          background: 'var(--bg-card)',
          color: 'var(--text-muted)',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 13,
          padding: 0,
          marginBottom: 8,
          flexShrink: 0,
          lineHeight: 1,
          alignSelf: collapsed ? 'center' : 'flex-start',
        }}
      >
        {collapsed ? '›' : '‹'}
      </button>

      {/* Nav Items */}
      {NAV_ITEMS.map((item) => (
        <NavButton
          key={item.path}
          icon={item.icon}
          label={item.label}
          active={location.pathname.startsWith(item.path)}
          collapsed={collapsed}
          onClick={() => navigate(item.path)}
        />
      ))}

      {/* Admin nav item — only visible to admins */}
      {user?.role === 'admin' && (
        <NavButton
          icon="🛡️"
          label="Admin"
          active={location.pathname.startsWith('/admin')}
          collapsed={collapsed}
          onClick={() => navigate('/admin')}
        />
      )}

      <div style={{ flex: 1 }} />

      {/* Theme toggle */}
      <NavButton
        icon="◑"
        label="Toggle theme"
        active={false}
        collapsed={collapsed}
        onClick={toggle}
      />

      {/* User avatar */}
      <button
        onClick={() => navigate('/settings')}
        aria-label="Profile"
        title={user?.full_name ?? 'Profile'}
        style={{
          height: 42,
          width: collapsed ? 42 : '100%',
          borderRadius: 10,
          border: 'none',
          background: 'transparent',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: collapsed ? 'center' : 'flex-start',
          gap: 10,
          padding: collapsed ? 0 : '0 12px',
          flexShrink: 0,
          overflow: 'hidden',
          whiteSpace: 'nowrap',
        }}
      >
        <div style={{
          width: 28,
          height: 28,
          borderRadius: '50%',
          background: 'linear-gradient(135deg, var(--accent), var(--purple))',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 11,
          fontWeight: 800,
          color: '#fff',
          flexShrink: 0,
        }}>
          {user ? getInitials(user.full_name) : '?'}
        </div>
        {!collapsed && (
          <span style={{
            fontSize: 13,
            fontFamily: 'Syne, sans-serif',
            fontWeight: 600,
            color: 'var(--text-secondary)',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}>
            {user?.full_name ?? 'Profile'}
          </span>
        )}
      </button>

      {/* Logout */}
      <NavButton
        icon="→"
        label="Sign out"
        active={false}
        collapsed={collapsed}
        onClick={() => logout.mutate()}
      />
    </nav>
  )
}
