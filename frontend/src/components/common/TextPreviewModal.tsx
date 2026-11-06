import { Modal } from '@/components/common/Modal'

interface TextPreviewModalProps {
  open: boolean
  title: string
  text: string | null
  truncated?: boolean
  loading?: boolean
  onClose: () => void
}

// Plain-text preview (#150). The content is rendered as a React text node in
// a <pre>, never as HTML, so a file containing markup or <script> shows as text.
export function TextPreviewModal({ open, title, text, truncated, loading, onClose }: TextPreviewModalProps) {
  return (
    <Modal open={open} onClose={onClose} title={title} size="lg">
      {loading ? (
        <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Loading preview…</p>
      ) : (
        <>
          <pre
            data-testid="text-preview"
            style={{
              maxHeight: '65vh',
              overflow: 'auto',
              margin: 0,
              padding: 12,
              fontSize: 12,
              lineHeight: 1.5,
              fontFamily: 'JetBrains Mono, monospace',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              background: 'var(--bg-base)',
              border: '1px solid var(--border)',
              borderRadius: 6,
              color: 'var(--text-primary)',
            }}
          >
            {text ?? ''}
          </pre>
          {truncated && (
            <p style={{ marginTop: 8, fontSize: 12, color: 'var(--text-muted)' }}>
              Showing the first 1 MB only. Download the file to see all of it.
            </p>
          )}
        </>
      )}
    </Modal>
  )
}
