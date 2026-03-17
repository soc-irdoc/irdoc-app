interface EmptyStateProps {
  icon?: string
  title: string
  description?: string
  action?: React.ReactNode
}

export function EmptyState({ icon = '📭', title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-4 text-center">
      <span style={{ fontSize: 48 }}>{icon}</span>
      <div>
        <p className="text-base font-bold" style={{ color: 'var(--text-primary)' }}>{title}</p>
        {description && (
          <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>{description}</p>
        )}
      </div>
      {action}
    </div>
  )
}
