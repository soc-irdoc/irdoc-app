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

/**
 * Message for a failed login. Only a backend `detail` string means the
 * credentials themselves were rejected; a 502 while the backend restarts, the
 * login rate limit, or an unreachable server must not read as a wrong password.
 */
export function getLoginErrorMessage(err: unknown): string {
  if (!isAxiosError(err)) return 'Login failed. Please try again.'
  const status = err.response?.status
  const detail = err.response?.data?.detail
  if (status === 429) return 'Too many login attempts. Wait a minute and try again.'
  if (!err.response || (status !== undefined && status >= 500)) {
    return 'Cannot reach the IRDoc server (it may still be starting). Try again in a moment.'
  }
  if (typeof detail === 'string') return detail
  if (status === 422) return 'Enter a valid email address and password.'
  return 'Invalid credentials'
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
