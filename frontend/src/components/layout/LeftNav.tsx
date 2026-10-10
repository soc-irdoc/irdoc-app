import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useThemeStore } from '@/stores/themeStore'
import { useLogout } from '@/hooks/useAuth'
import { useAuthStore } from '@/stores/authStore'
import { getInitials } from '@/lib/utils'
import { BrandLogo } from '@/components/common/BrandLogo'
import { VersionBadge } from '@/components/common/VersionBadge'
import type { IconType } from 'react-icons'
import {
  FaAnglesLeft, FaBars, FaBolt, FaBoxArchive, FaBuilding, FaCircleHalfStroke, FaClipboardList, FaFileLines,
  FaGaugeHigh, FaGear, FaHardDrive, FaPlug, FaRightFromBracket, FaScroll,
} from 'react-icons/fa6'

interface NavItem {
  icon: IconType
  label: string
  path: string
}

const NAV_ITEMS: NavItem[] = [
  { icon: FaGaugeHigh, label: 'Overview',  path: '/overview' },
  { icon: FaBolt, label: 'Incidents', path: '/incidents' },
  { icon: FaGear, label: 'Settings', path: '/settings' },
]

const MANAGEMENT_ITEMS: NavItem[] = [
  { icon: FaBuilding, label: 'Org Settings', path: '/admin/org' },
  { icon: FaHardDrive, label: 'Storage', path: '/admin/storage' },
  { icon: FaBoxArchive, label: 'Backups', path: '/admin/backups' },
  { icon: FaClipboardList, label: 'Incident Templates', path: '/admin/templates' },
  { icon: FaFileLines, label: 'Report Templates', path: '/report-templates' },
  { icon: FaPlug, label: 'Integrations', path: '/admin/integrations' },
  { icon: FaScroll, label: 'Audit Log', path: '/admin/audit' },
]

function NavButton({
  icon: NavIcon,
  label,
  active,
  collapsed,
  onClick,
}: {
  icon: IconType
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
      <NavIcon size={17} aria-hidden="true" style={{ flexShrink: 0 }} />
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
        <BrandLogo
          size={70}
          title="IRDoc"
          onClick={() => navigate('/overview')}
          style={{ cursor: 'pointer' }}
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

      {/* Collapse toggle - nav item at top, above all other items */}
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
        {collapsed
          ? <FaBars size={17} aria-hidden="true" style={{ flexShrink: 0 }} />
          : <FaAnglesLeft size={17} aria-hidden="true" style={{ flexShrink: 0 }} />}
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

      {/* Management section - admin only */}
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
        icon={FaCircleHalfStroke}
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
        icon={FaRightFromBracket}
        label="Sign out"
        active={false}
        collapsed={collapsed}
        onClick={() => logout.mutate()}
      />

      {/* Version */}
      <div style={{ display: 'flex', justifyContent: 'center', padding: '6px 4px 0', flexShrink: 0 }}>
        <VersionBadge compact={collapsed} />
      </div>
    </nav>
  )
}
