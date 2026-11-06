import { describe, expect, it } from 'vitest'
import { previewKind } from '@/lib/preview'

describe('previewKind (#150)', () => {
  it('previews only allowlisted types', () => {
    expect(previewKind('image/png')).toBe('image')
    expect(previewKind('image/webp')).toBe('image')
    expect(previewKind('application/pdf')).toBe('pdf')
    expect(previewKind('text/plain')).toBe('text')
    expect(previewKind('text/csv; charset=utf-8')).toBe('text')
    expect(previewKind('application/json')).toBe('text')
  })

  it('never previews types that can carry script, or unknown ones', () => {
    for (const mime of ['image/svg+xml', 'text/html', 'application/xhtml+xml', 'application/octet-stream',
      'application/zip', 'application/msword', '', null, undefined]) {
      expect(previewKind(mime)).toBe('none')
    }
  })
})
