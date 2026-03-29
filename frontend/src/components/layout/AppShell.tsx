import { type ReactNode } from 'react'
import { LeftNav } from './LeftNav'
import { useUIStore } from '@/stores/uiStore'

interface AppShellProps {
  children: ReactNode
}

export function AppShell({ children }: AppShellProps) {
  const wsConnected = useUIStore((s: { wsConnected: boolean }) => s.wsConnected)

  return (
    <div
      style={{
        display: 'flex',
        height: '100vh',
        overflow: 'hidden',
        background: 'var(--bg-base)',
      }}
    >
      <LeftNav />
      <main
        style={{
          flex: 1,
          display: 'flex',
          overflow: 'hidden',
          flexDirection: 'column',
        }}
      >
        {!wsConnected && (
          <div
            role="alert"
            style={{
              background: 'var(--yellow-dim, rgba(250,204,21,0.15))',
              borderBottom: '1px solid var(--yellow, #facc15)',
              color: 'var(--yellow, #facc15)',
              fontSize: 13,
              padding: '6px 16px',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              flexShrink: 0,
            }}
          >
            <span>⚠</span>
            <span>Real-time connection lost. Reconnecting… Live updates are paused.</span>
          </div>
        )}
        {children}
      </main>
    </div>
  )
}
