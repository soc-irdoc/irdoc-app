import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useThemeStore } from '@/stores/themeStore'
import { useLogout } from '@/hooks/useAuth'
import { useAuthStore } from '@/stores/authStore'
import { getInitials } from '@/lib/utils'
import irdocDark from '@/assets/irdoc_dark.svg'
import irdocLight from '@/assets/irdoc_light.svg'

interface NavItem {
  icon: string
  label: string
  path: string
}

const NAV_ITEMS: NavItem[] = [
  { icon: '◈',  label: 'Overview',  path: '/overview' },
  { icon: 'high_voltage_color.svg', label: 'Incidents', path: '/incidents' },
  { icon: 'gear_color.svg',  label: 'Settings', path: '/settings' },
]

const MANAGEMENT_ITEMS: NavItem[] = [
  { icon: 'gear_color.svg', label: 'Org Settings', path: '/admin/org' },
  { icon: 'file_cabinet_color.svg', label: 'Storage', path: '/admin/storage' },
  { icon: 'floppy_disk_color.svg', label: 'Backups', path: '/admin/backups' },
  { icon: 'clipboard_color.svg', label: 'Incident Templates', path: '/admin/templates' },
  { icon: 'page_facing_up_color.svg', label: 'Report Templates', path: '/report-templates' },
  { icon: 'link_color.svg', label: 'Integrations', path: '/admin/integrations' },
  { icon: 'scroll_color.svg', label: 'Audit Log', path: '/admin/audit' },
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
        width: '100%',
        height: 42,
        borderRadius: 10,
        border: 'none',
        background: active ? 'var(--accent-dim)' : 'transparent',
        color: active ? 'var(--accent)' : 'var(--text-muted)',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'flex-start',
        gap: 10,
        fontSize: 18,
        padding: '0 12px',
        transition: 'background 0.15s, color 0.15s, box-shadow 0.15s',
        position: 'relative',
        flexShrink: 0,
        whiteSpace: 'nowrap',
        overflow: 'hidden',
        boxShadow: active && !collapsed ? 'inset 2px 0 0 var(--accent)' : 'none',
      }}
    >
      {icon.endsWith('.svg')
        ? <img src={`/icons/${icon}`} width={20} height={20} alt="" aria-hidden="true" style={{ flexShrink: 0 }} />
        : <span style={{ flexShrink: 0, lineHeight: 1 }}>{icon}</span>
      }
      <span style={{
        fontSize: 13,
        fontFamily: 'Syne, sans-serif',
        fontWeight: 600,
        color: active ? 'var(--accent)' : 'var(--text-secondary)',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        opacity: collapsed ? 0 : 1,
        transition: 'opacity 0.12s',
      }}>
        {label}
      </span>
    </button>
  )
}

export function LeftNav() {
  const navigate = useNavigate()
  const location = useLocation()
  const { toggle, theme } = useThemeStore()
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
        background: 'var(--bg-surface)',
        borderRight: '1px solid var(--border)',
        boxShadow: '2px 0 12px rgba(0,0,0,0.3)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'stretch',
        padding: '16px 8px',
        gap: 4,
        flexShrink: 0,
        zIndex: 100,
        transition: 'width 0.25s ease',
        overflow: 'hidden',
      }}
    >
      {/* Logo row */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'flex-start',
        gap: 10,
        flexShrink: 0,
        padding: '0 2px',
      }}>
        <img
          src={theme === 'dark' ? irdocDark : irdocLight}
          alt="IRDoc"
          title="IRDoc"
          onClick={() => navigate('/overview')}
          style={{ width: 70, height: 70, objectFit: 'contain', cursor: 'pointer', flexShrink: 0 }}
        />

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

      {/* Collapse toggle — nav item at top, above all other items */}
      <button
        onClick={toggleCollapsed}
        aria-label={collapsed ? 'Expand navigation' : 'Collapse navigation'}
        title={collapsed ? 'Expand navigation' : 'Collapse navigation'}
        style={{
          width: '100%',
          height: 42,
          borderRadius: 10,
          border: 'none',
          background: 'transparent',
          color: 'var(--text-muted)',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'flex-start',
          gap: 10,
          padding: '0 12px',
          fontSize: 18,
          flexShrink: 0,
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          borderBottom: '1px solid var(--border)',
          marginBottom: 4,
        }}
      >
        <span style={{ flexShrink: 0, lineHeight: 1 }}>{collapsed ? '☰' : '◀'}</span>
        <span style={{
          fontSize: 13,
          fontFamily: 'Syne, sans-serif',
          fontWeight: 600,
          color: 'var(--text-muted)',
          opacity: collapsed ? 0 : 1,
          transition: 'opacity 0.12s',
        }}>
          Collapse
        </span>
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

      {/* Management section — admin only */}
      {user?.role === 'admin' && (
        <>
          <div style={{
            margin: collapsed ? '8px 0 4px' : '10px 4px 4px',
            borderTop: '1px solid var(--border)',
            paddingTop: collapsed ? 0 : 8,
          }}>
            {!collapsed && (
              <span style={{
                fontSize: 10,
                fontWeight: 700,
                letterSpacing: '0.08em',
                color: 'var(--text-muted)',
                fontFamily: 'Syne, sans-serif',
                textTransform: 'uppercase',
                padding: '0 4px',
                display: 'block',
                marginBottom: 4,
              }}>
                Management
              </span>
            )}
          </div>
          {MANAGEMENT_ITEMS.map((item) => (
            <NavButton
              key={item.path}
              icon={item.icon}
              label={item.label}
              active={location.pathname === item.path}
              collapsed={collapsed}
              onClick={() => navigate(item.path)}
            />
          ))}
        </>
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
          width: '100%',
          borderRadius: 10,
          border: 'none',
          background: 'transparent',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'flex-start',
          gap: 10,
          padding: '0 12px',
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
        <span style={{
          fontSize: 13,
          fontFamily: 'Syne, sans-serif',
          fontWeight: 600,
          color: 'var(--text-secondary)',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          opacity: collapsed ? 0 : 1,
          transition: 'opacity 0.12s',
        }}>
          {user?.full_name ?? 'Profile'}
        </span>
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
