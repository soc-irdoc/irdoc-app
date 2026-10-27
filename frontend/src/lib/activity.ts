// User activity and the session's idle timeout (#123).
//
// The server ends a session that hasn't refreshed within the idle timeout,
// and ends every session at its absolute lifetime. This module is the client
// half: it notes when the user last did something (shared across tabs), so
// tokens are only refreshed for someone actually using the app, and it signs
// the tab out once the idle timeout passes, with a warning a minute before.

import { useUIStore } from '@/stores/uiStore'

export interface SessionMeta {
  idle_minutes: number
  expires_at: string // ISO: the absolute end of the session
}

const STORAGE_KEY = 'irdoc:last-activity'
const STORAGE_WRITE_EVERY_MS = 15_000
const CHECK_EVERY_MS = 15_000
const WARN_BEFORE_MS = 60_000
const ACTIVITY_EVENTS = ['pointerdown', 'keydown', 'wheel', 'touchstart', 'mousemove'] as const

let lastActivity = Date.now()
let lastStorageWrite = 0
let idleMs = 60 * 60_000
let sessionEndsAt: number | null = null
let checkTimer: ReturnType<typeof setInterval> | null = null
let warned = false
let endWarned = false
let onIdleCallback: (() => void) | null = null

function readShared(): number {
  try {
    return Number(localStorage.getItem(STORAGE_KEY)) || 0
  } catch {
    return 0
  }
}

/** Record user activity now. Throttled when shared with other tabs. */
export function markActivity(now = Date.now()) {
  lastActivity = now
  warned = false
  if (now - lastStorageWrite >= STORAGE_WRITE_EVERY_MS) {
    lastStorageWrite = now
    try {
      localStorage.setItem(STORAGE_KEY, String(now))
    } catch {
      // Private mode or blocked storage: this tab's own activity still counts.
    }
  }
}

/** Last activity in this tab or any other tab of the app. */
export function getLastActivity(): number {
  return Math.max(lastActivity, readShared())
}

/** True if the user did something at or after `since` (ms epoch). */
export function hasActivitySince(since: number): boolean {
  return getLastActivity() >= since
}

/** Apply the session limits the server sent with a login or refresh. */
export function applySessionMeta(meta: SessionMeta | undefined | null) {
  if (!meta) return
  if (meta.idle_minutes > 0) idleMs = meta.idle_minutes * 60_000
  const end = Date.parse(meta.expires_at)
  sessionEndsAt = Number.isNaN(end) ? null : end
}

function check() {
  const now = Date.now()
  const idleFor = now - getLastActivity()
  const addToast = useUIStore.getState().addToast

  if (idleFor >= idleMs) {
    const cb = onIdleCallback
    stopActivityTracking()
    cb?.()
    return
  }
  if (!warned && idleMs - idleFor <= WARN_BEFORE_MS) {
    warned = true
    addToast("You'll be signed out in a minute because of inactivity.", 'info')
  }
  if (!endWarned && sessionEndsAt !== null && sessionEndsAt - now <= 5 * 60_000) {
    endWarned = true
    addToast('Your session ends in 5 minutes. Save your work - you will need to sign in again.', 'info')
  }
}

const onActivity = () => markActivity()

/** Start watching for idleness; `onIdle` runs once the idle timeout passes. */
export function startActivityTracking(onIdle: () => void) {
  stopActivityTracking()
  onIdleCallback = onIdle
  markActivity()
  warned = false
  endWarned = false
  ACTIVITY_EVENTS.forEach((e) => window.addEventListener(e, onActivity, { passive: true }))
  checkTimer = setInterval(check, CHECK_EVERY_MS)
}

export function stopActivityTracking() {
  ACTIVITY_EVENTS.forEach((e) => window.removeEventListener(e, onActivity))
  if (checkTimer) clearInterval(checkTimer)
  checkTimer = null
  onIdleCallback = null
}
