import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TextPreviewModal } from '../TextPreviewModal'

// #150: text previews are shown as text, never interpreted as HTML.
describe('TextPreviewModal', () => {
  it('renders markup and <script> as literal text', () => {
    const text = '<script>window.pwned = true</script><img src=x onerror="alert(1)"><b>bold</b>'
    render(<TextPreviewModal open title="notes.txt" text={text} onClose={vi.fn()} />)

    expect(screen.getByTestId('text-preview').textContent).toBe(text)
    expect(document.querySelector('script')).toBeNull()
    expect(document.querySelector('img')).toBeNull()
    expect(document.querySelector('b')).toBeNull()
  })

  it('says when the preview is truncated', () => {
    render(<TextPreviewModal open title="big.log" text="aaa" truncated onClose={vi.fn()} />)
    expect(screen.getByText(/first 1 MB only/i)).toBeInTheDocument()
  })
})
