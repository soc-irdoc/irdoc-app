import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { PdfPreviewModal } from '../PdfPreviewModal'

function mockFetch(status: number, headers: Record<string, string>) {
  const fn = vi.fn().mockResolvedValue(new Response(null, { status, headers }))
  vi.stubGlobal('fetch', fn)
  return fn
}

// #137: when a proxy's header blocks the frame, say which one.
describe('PdfPreviewModal', () => {
  afterEach(() => vi.unstubAllGlobals())

  it("shows the frame when the headers are IRDoc's own", async () => {
    const fetchMock = mockFetch(200, { 'x-frame-options': 'SAMEORIGIN', 'content-type': 'application/pdf' })
    render(<PdfPreviewModal url="/api/v1/files/tok" onClose={vi.fn()} />)

    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/v1/files/tok', expect.anything()))
    expect(screen.getByTitle('PDF preview')).toHaveAttribute('src', '/api/v1/files/tok')
    expect(screen.queryByTestId('pdf-preview-blocked')).toBeNull()
  })

  it('names the blocking header instead of an empty frame', async () => {
    mockFetch(200, { 'x-frame-options': 'SAMEORIGIN, DENY' })
    render(<PdfPreviewModal url="/api/v1/files/tok" onClose={vi.fn()} />)

    const alert = await screen.findByTestId('pdf-preview-blocked')
    expect(alert).toHaveTextContent('X-Frame-Options: SAMEORIGIN, DENY')
    expect(alert).toHaveTextContent(/reverse proxy/)
    expect(screen.queryByTitle('PDF preview')).toBeNull()
    expect(screen.getByText('Open in new tab')).toHaveAttribute('href', '/api/v1/files/tok')
  })

  it('reports an error status', async () => {
    mockFetch(403, {})
    render(<PdfPreviewModal url="/api/v1/files/tok" onClose={vi.fn()} />)
    expect(await screen.findByTestId('pdf-preview-blocked')).toHaveTextContent('HTTP 403')
  })

  it('keeps the frame when the check itself fails', async () => {
    const fetchMock = vi.fn().mockRejectedValue(new TypeError('network'))
    vi.stubGlobal('fetch', fetchMock)
    render(<PdfPreviewModal url="/api/v1/files/tok" onClose={vi.fn()} />)
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalled())
    expect(screen.getByTitle('PDF preview')).toBeInTheDocument()
  })
})
