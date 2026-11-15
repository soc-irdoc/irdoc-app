import { useEffect, useState } from 'react'
import { Modal } from '@/components/common/Modal'
import { frameBlockReason, type FrameBlock } from '@/lib/frameBlock'

interface PdfPreviewModalProps {
  url: string | null
  onClose: () => void
}

type Problem = FrameBlock | { status: number }

// When the browser refuses the frame, Chrome only says "This content is
// blocked. Contact the site owner" (#137). Read the same response headers the
// frame gets and, if one of them blocks it, say which one instead. The body
// isn't needed: the request is aborted once the headers are in.
function useFrameProblem(url: string | null): Problem | null {
  const [problem, setProblem] = useState<Problem | null>(null)
  useEffect(() => {
    setProblem(null)
    if (!url) return
    const ctrl = new AbortController()
    fetch(url, { signal: ctrl.signal, credentials: 'same-origin' })
      .then((res) => {
        if (ctrl.signal.aborted) return
        if (!res.ok) setProblem({ status: res.status })
        else setProblem(frameBlockReason(res.headers, window.location.origin))
        ctrl.abort()
      })
      .catch(() => {
        // Network error or aborted: leave the frame to show what it can.
      })
    return () => ctrl.abort()
  }, [url])
  return problem
}

export function PdfPreviewModal({ url, onClose }: PdfPreviewModalProps) {
  const problem = useFrameProblem(url)
  if (!url) return null
  return (
    <Modal open onClose={onClose} title="Document Preview" size="lg">
      {problem ? (
        <div
          role="alert"
          data-testid="pdf-preview-blocked"
          style={{
            padding: 16,
            fontSize: 13,
            lineHeight: 1.5,
            background: 'var(--bg-base)',
            border: '1px solid var(--border)',
            borderRadius: 6,
            color: 'var(--text-primary)',
          }}
        >
          {'status' in problem ? (
            <p style={{ margin: 0 }}>
              The file could not be loaded for the preview (HTTP {problem.status}). Try opening it in a new tab.
            </p>
          ) : (
            <>
              <p style={{ margin: '0 0 8px' }}>
                Your browser won't show this file inside IRDoc because of a header on the response:
              </p>
              <code style={{ display: 'block', wordBreak: 'break-all', marginBottom: 8 }}>{problem.header}</code>
              <p style={{ margin: '0 0 8px' }}>{problem.why}</p>
              <p style={{ margin: 0, color: 'var(--text-muted)' }}>
                IRDoc itself sends <code>X-Frame-Options: SAMEORIGIN</code> and{' '}
                <code>frame-ancestors 'self'</code> for files, so this header is most likely added by a
                reverse proxy in front of IRDoc. An administrator can stop the proxy adding it for{' '}
                <code>/api/v1/files/</code>. Until then, open the file in a new tab.
              </p>
            </>
          )}
        </div>
      ) : (
        <iframe
          src={url}
          style={{ width: '100%', height: '70vh', border: 'none', borderRadius: 4 }}
          title="PDF preview"
        />
      )}
      {/* Fallback for browsers or proxies that still won't render it inline (#137) */}
      <div style={{ marginTop: 8, fontSize: 12, textAlign: 'right' }}>
        <a href={url} target="_blank" rel="noopener noreferrer">Open in new tab</a>
      </div>
    </Modal>
  )
}
