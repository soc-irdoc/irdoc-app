import { useUIStore } from '@/stores/uiStore'

export function ToastContainer() {
  const { toasts, removeToast } = useUIStore()

  if (toasts.length === 0) return null

  return (
    <div className="fixed bottom-6 right-6 z-[100] flex flex-col gap-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className="animate-slide-in flex items-center gap-3 px-4 py-3 rounded-card min-w-[280px] max-w-sm"
          style={{
            background: 'var(--bg-elevated)',
            border: `1px solid ${
              toast.type === 'success' ? 'var(--green)' :
              toast.type === 'error'   ? 'var(--red)' :
                                         'var(--border)'
            }`,
            boxShadow: 'var(--shadow)',
          }}
        >
          <span style={{ fontSize: 16 }}>
            {toast.type === 'success' ? '✓' : toast.type === 'error' ? '✕' : 'ℹ'}
          </span>
          <p
            className="flex-1 text-sm font-medium"
            style={{ color: 'var(--text-primary)' }}
          >
            {toast.message}
          </p>
          <button
            className="icon-btn"
            onClick={() => removeToast(toast.id)}
            aria-label="Dismiss"
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  )
}
