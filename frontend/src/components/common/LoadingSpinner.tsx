interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export function LoadingSpinner({ size = 'md', className }: SpinnerProps) {
  const sizes = { sm: 'w-4 h-4', md: 'w-8 h-8', lg: 'w-12 h-12' }
  return (
    <div
      className={`${sizes[size]} border-2 border-current border-t-transparent rounded-full animate-spin ${className ?? ''}`}
      style={{ color: 'var(--accent)' }}
      role="status"
      aria-label="Loading"
    />
  )
}

export function PageLoader() {
  return (
    <div className="flex-1 flex items-center justify-center" style={{ background: 'var(--bg-base)' }}>
      <LoadingSpinner size="lg" />
    </div>
  )
}
