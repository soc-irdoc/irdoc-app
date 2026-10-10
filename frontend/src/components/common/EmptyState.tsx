import type { IconType } from 'react-icons'
import { FaInbox } from 'react-icons/fa6'

interface EmptyStateProps {
  icon?: IconType
  title: string
  description?: string
  action?: React.ReactNode
}

export function EmptyState({ icon: EmptyIcon = FaInbox, title, description, action }: EmptyStateProps) {
  return (
    <div className="animate-fade-in flex flex-col items-center justify-center py-16 gap-5 text-center">
      <div style={{
        width: 72,
        height: 72,
        borderRadius: '50%',
        background: 'var(--bg-elevated)',
        border: '1px solid var(--border)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}>
        <EmptyIcon size={30} aria-hidden="true" style={{ color: 'var(--text-muted)' }} />
      </div>
      <div>
        <p style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 4 }}>{title}</p>
        {description && (
          <p style={{ fontSize: 13, color: 'var(--text-muted)', maxWidth: 320 }}>{description}</p>
        )}
      </div>
      {action}
    </div>
  )
}
