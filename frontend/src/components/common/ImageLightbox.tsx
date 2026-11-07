import { useEffect, useRef } from 'react'

interface ImageLightboxProps {
  url: string | null
  alt?: string
  onClose: () => void
}

// Full-screen image preview. Click or Escape closes it.
export function ImageLightbox({ url, alt = 'Attachment preview', onClose }: ImageLightboxProps) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!url) return
    ref.current?.focus()
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [url, onClose])

  if (!url) return null
  return (
    <div
      ref={ref}
      role="dialog"
      aria-modal="true"
      aria-label="Image preview"
      tabIndex={-1}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 100,
        background: 'rgba(0,0,0,0.85)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        cursor: 'zoom-out',
        outline: 'none',
      }}
      onClick={onClose}
    >
      <img
        src={url}
        alt={alt}
        style={{ maxWidth: '90vw', maxHeight: '90vh', borderRadius: 8, objectFit: 'contain' }}
        onClick={(e) => e.stopPropagation()}
      />
    </div>
  )
}
