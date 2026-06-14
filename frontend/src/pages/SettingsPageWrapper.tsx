import { AppShell } from '@/components/layout/AppShell'
import { SettingsPage } from '@/components/settings/SettingsPage'

export function SettingsPageWrapper() {
  return (
    <AppShell>
      <div style={{ flex: 1, overflowY: 'auto', background: 'var(--bg-base)' }}>
        <SettingsPage />
      </div>
    </AppShell>
  )
}
