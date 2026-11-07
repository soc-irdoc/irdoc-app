import { Modal } from '@/components/common/Modal'

interface PdfPreviewModalProps {
  url: string | null
  onClose: () => void
}

export function PdfPreviewModal({ url, onClose }: PdfPreviewModalProps) {
  if (!url) return null
  return (
    <Modal open onClose={onClose} title="Document Preview" size="lg">
      <iframe
        src={url}
        style={{ width: '100%', height: '70vh', border: 'none', borderRadius: 4 }}
        title="PDF preview"
      />
      {/* Fallback for browsers or proxies that still won't render it inline (#137) */}
      <div style={{ marginTop: 8, fontSize: 12, textAlign: 'right' }}>
        <a href={url} target="_blank" rel="noopener noreferrer">Open in new tab</a>
      </div>
    </Modal>
  )
}
