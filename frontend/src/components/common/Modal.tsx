import { useEffect, type ReactNode } from 'react'

interface ModalProps {
  open?: boolean
  onClose: () => void
  title: string
  children: ReactNode
  size?: 'sm' | 'md' | 'lg'
  maxWidth?: number
}

export type { ModalProps }

export function Modal({ open = true, onClose, title, children, size = 'md', maxWidth }: ModalProps) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    if (open) document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open, onClose])

  if (!open) return null

  const widths = { sm: 'max-w-sm', md: 'max-w-lg', lg: 'max-w-2xl' }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)' }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div
        className={`w-full ${widths[size]} animate-fade-in rounded-card`}
        style={{
          background: 'var(--bg-elevated)',
          border: '1px solid var(--border)',
          boxShadow: 'var(--shadow)',
          ...(maxWidth !== undefined ? { maxWidth } : {}),
        }}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-6 py-4"
          style={{ borderBottom: '1px solid var(--border)' }}
        >
          <h2
            className="text-base font-bold"
            style={{ color: 'var(--text-primary)' }}
          >
            {title}
          </h2>
          <button
            className="icon-btn"
            onClick={onClose}
            aria-label="Close modal"
          >
            <img src="/icons/multiply_color.svg" width={14} height={14} alt="" aria-hidden="true" />
          </button>
        </div>
        {/* Body */}
        <div className="p-6">{children}</div>
      </div>
    </div>
  )
}
