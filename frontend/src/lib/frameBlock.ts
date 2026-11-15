// Why the browser would refuse to show a file inside the PDF preview frame
// (#137). Chrome only says "This content is blocked. Contact the site owner",
// so the preview reads the file's response headers itself and names the one
// that blocks it. IRDoc sends `X-Frame-Options: SAMEORIGIN` and
// `frame-ancestors 'self'` for /api/v1/files/; a reverse proxy in front of
// IRDoc that adds its own security headers is the usual culprit.

export interface FrameBlock {
  /** The header as the browser received it, e.g. "X-Frame-Options: DENY". */
  header: string
  /** One sentence on why that blocks the preview. */
  why: string
}

function xfoBlock(value: string | null): FrameBlock | null {
  if (!value) return null
  // fetch() joins repeated headers with ", ". Per the HTML spec, a DENY, or
  // more than one distinct value, blocks every frame.
  const values = [...new Set(value.split(',').map((v) => v.trim().toLowerCase()).filter(Boolean))]
  if (values.includes('deny')) {
    return { header: `X-Frame-Options: ${value}`, why: 'DENY forbids showing the file in any frame, including IRDoc\'s own.' }
  }
  if (values.length > 1) {
    return {
      header: `X-Frame-Options: ${value}`,
      why: 'The header was sent more than once with different values, and browsers then block the frame.',
    }
  }
  return null
}

function cspBlock(value: string | null, pageOrigin: string): FrameBlock | null {
  if (!value) return null
  // Repeated CSP headers arrive joined with ", "; the browser enforces each.
  for (const policy of value.split(',')) {
    const directives = policy.split(';').map((d) => d.trim().split(/\s+/)).filter((d) => d[0])
    for (const [name, ...sources] of directives) {
      const directive = name.toLowerCase()
      if (directive === 'sandbox') {
        return {
          header: `Content-Security-Policy: ${policy.trim()}`,
          why: 'The sandbox directive stops the browser\'s PDF viewer from loading.',
        }
      }
      if (directive === 'frame-ancestors') {
        const allowed = sources.some((s) => {
          const src = s.toLowerCase()
          return src === "'self'" || src === '*' || src === pageOrigin.toLowerCase()
        })
        if (!allowed) {
          return {
            header: `Content-Security-Policy: ${policy.trim()}`,
            why: `frame-ancestors ${sources.join(' ') || "(empty)"} does not allow IRDoc's own pages to frame the file.`,
          }
        }
      }
    }
  }
  return null
}

/** The first header in `headers` that stops `pageOrigin` from framing the
 * response, or null when nothing in the headers blocks it. */
export function frameBlockReason(headers: Headers, pageOrigin: string): FrameBlock | null {
  return (
    xfoBlock(headers.get('x-frame-options')) ??
    cspBlock(headers.get('content-security-policy'), pageOrigin)
  )
}
