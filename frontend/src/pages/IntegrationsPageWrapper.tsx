import { AppShell } from '@/components/layout/AppShell'
import { IntegrationsPage } from '@/components/integrations/IntegrationsPage'

export function IntegrationsPageWrapper() {
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
        <IntegrationsPage />
      </div>
    </AppShell>
  )
}
