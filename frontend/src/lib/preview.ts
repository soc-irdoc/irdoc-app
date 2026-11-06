// Which attachments can be previewed in the browser (#150). Decided only by
// the MIME type the server detected at upload, never the file name. SVG and
// HTML are left out on purpose: they can carry script.

export type PreviewKind = 'image' | 'pdf' | 'text' | 'none'

const IMAGE_MIMES = new Set(['image/png', 'image/jpeg', 'image/gif', 'image/webp'])
const TEXT_MIMES = new Set(['text/plain', 'text/csv', 'application/json'])

export function previewKind(mime: string | null | undefined): PreviewKind {
  if (!mime) return 'none'
  const m = mime.toLowerCase().split(';')[0].trim()
  if (IMAGE_MIMES.has(m)) return 'image'
  if (m === 'application/pdf') return 'pdf'
  if (TEXT_MIMES.has(m)) return 'text'
  return 'none'
}
