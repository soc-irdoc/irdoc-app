import { type ReactNode } from 'react'
import { LeftNav } from './LeftNav'

interface AppShellProps {
  children: ReactNode
}

export function AppShell({ children }: AppShellProps) {
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
        {children}
      </main>
    </div>
  )
}
