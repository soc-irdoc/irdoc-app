import { format, formatDistanceToNow, parseISO } from 'date-fns'
import { isAxiosError } from 'axios'

/** Extract a backend-supplied error detail from a caught request error, falling back to a default message. */
export function getErrorMessage(err: unknown, fallback: string): string {
  if (isAxiosError(err)) {
    const detail = err.response?.data?.detail
    if (typeof detail === 'string') return detail
  }
  return fallback
}

export function formatDateTime(iso: string): string {
  return format(parseISO(iso), 'yyyy-MM-dd HH:mm:ss')
}

export function formatDate(iso: string): string {
  return format(parseISO(iso), 'yyyy-MM-dd')
}

export function formatTime(iso: string): string {
  return format(parseISO(iso), 'HH:mm:ss')
}

export function formatRelative(iso: string): string {
  return formatDistanceToNow(parseISO(iso), { addSuffix: true })
}

export function formatNowDate(): string {
  return format(new Date(), 'yyyy-MM-dd')
}

export function formatNowTime(): string {
  return format(new Date(), 'HH:mm:ss')
}

export function formatNowISO(): string {
  return new Date().toISOString().slice(0, 19)
}

export function copyToClipboard(text: string): void {
  navigator.clipboard.writeText(text).catch(() => {
    // fallback
    const el = document.createElement('textarea')
    el.value = text
    document.body.appendChild(el)
    el.select()
    document.execCommand('copy')
    document.body.removeChild(el)
  })
}

export function fileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

export function isImageMime(mime: string): boolean {
  return mime.startsWith('image/')
}

export function cn(...classes: (string | undefined | false | null)[]): string {
  return classes.filter(Boolean).join(' ')
}

export function getInitials(name: string): string {
  return name
    .split(' ')
    .slice(0, 2)
    .map((n) => n[0]?.toUpperCase() ?? '')
    .join('')
}
