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
              background: 'rgba(227,179,65,0.10)',
              borderBottom: '1px solid var(--border)',
              borderLeft: '3px solid var(--yellow)',
              color: 'var(--yellow)',
              fontSize: 12,
              fontWeight: 600,
              padding: '7px 16px',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              flexShrink: 0,
              letterSpacing: '0.01em',
            }}
          >
            <span style={{ fontSize: 14 }}>⚠</span>
            <span>Real-time connection lost — reconnecting. Live updates are paused.</span>
          </div>
        )}
        {children}
      </main>
    </div>
  )
}
