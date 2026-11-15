import { describe, expect, it } from 'vitest'
import { frameBlockReason } from '@/lib/frameBlock'

const ORIGIN = 'https://irdoc.example.com'
const IRDOC_FILE_CSP =
  "default-src 'none'; style-src 'unsafe-inline'; img-src 'self' data:; object-src 'self'; frame-ancestors 'self';"

function h(init: Record<string, string>) {
  return new Headers(init)
}

// #137: name the header that stops the PDF preview frame.
describe('frameBlockReason', () => {
  it("accepts IRDoc's own file headers, even when nginx and the backend both send them", () => {
    const headers = h({
      'x-frame-options': 'SAMEORIGIN, SAMEORIGIN',
      'content-security-policy': `${IRDOC_FILE_CSP}, ${IRDOC_FILE_CSP}`,
    })
    expect(frameBlockReason(headers, ORIGIN)).toBeNull()
  })

  it('accepts a response without framing headers', () => {
    expect(frameBlockReason(h({}), ORIGIN)).toBeNull()
  })

  it('blames X-Frame-Options DENY added by a proxy', () => {
    const r = frameBlockReason(h({ 'x-frame-options': 'SAMEORIGIN, DENY' }), ORIGIN)
    expect(r?.header).toBe('X-Frame-Options: SAMEORIGIN, DENY')
    expect(r?.why).toMatch(/DENY/)
  })

  it('blames conflicting X-Frame-Options values', () => {
    const r = frameBlockReason(h({ 'x-frame-options': 'SAMEORIGIN, ALLOW-FROM https://x' }), ORIGIN)
    expect(r?.why).toMatch(/more than once/)
  })

  it("blames a second CSP with frame-ancestors 'none'", () => {
    const csp = `${IRDOC_FILE_CSP}, default-src 'self'; frame-ancestors 'none'`
    const r = frameBlockReason(h({ 'content-security-policy': csp }), ORIGIN)
    expect(r?.header).toBe("Content-Security-Policy: default-src 'self'; frame-ancestors 'none'")
  })

  it('accepts frame-ancestors naming the page origin', () => {
    const csp = `frame-ancestors ${ORIGIN}`
    expect(frameBlockReason(h({ 'content-security-policy': csp }), ORIGIN)).toBeNull()
  })

  it('blames frame-ancestors listing only another origin', () => {
    const csp = 'frame-ancestors https://other.example.com'
    expect(frameBlockReason(h({ 'content-security-policy': csp }), ORIGIN)).not.toBeNull()
  })

  it('blames a CSP sandbox, which stops the PDF viewer', () => {
    const r = frameBlockReason(h({ 'content-security-policy': 'sandbox' }), ORIGIN)
    expect(r?.why).toMatch(/sandbox/)
  })
})
