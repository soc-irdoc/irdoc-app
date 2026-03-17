import { AppShell } from '@/components/layout/AppShell'
import { SettingsPage } from '@/components/settings/SettingsPage'

export function SettingsPageWrapper() {
  return (
    <AppShell>
      <div
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          background: 'var(--bg-base)',
        }}
      >
        {/* Settings TopBar */}
        <div
          style={{
            height: 56,
            background: 'var(--bg-surface)',
            borderBottom: '1px solid var(--border)',
            display: 'flex',
            alignItems: 'center',
            padding: '0 24px',
            flexShrink: 0,
          }}
        >
          <span
            style={{
              fontFamily: 'Syne, sans-serif',
              fontWeight: 800,
              fontSize: 16,
              color: 'var(--text-primary)',
            }}
          >
            ⚙ Settings
          </span>
        </div>
        <div style={{ flex: 1, overflowY: 'auto' }}>
          <SettingsPage />
        </div>
      </div>
    </AppShell>
  )
}
