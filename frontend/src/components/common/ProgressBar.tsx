interface ProgressBarProps {
  value: number  // 0-100
  className?: string
  color?: string
}

export function ProgressBar({ value, className, color = 'var(--accent)' }: ProgressBarProps) {
  return (
    <div
      className={`h-1 rounded-full overflow-hidden ${className ?? ''}`}
      style={{ background: 'var(--bg-elevated)' }}
    >
      <div
        className="h-full rounded-full transition-all duration-300"
        style={{ width: `${Math.min(100, Math.max(0, value))}%`, background: color }}
      />
    </div>
  )
}
