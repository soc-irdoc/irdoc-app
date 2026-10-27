import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  applySessionMeta,
  hasActivitySince,
  markActivity,
  startActivityTracking,
  stopActivityTracking,
} from '@/lib/activity'
import { useUIStore } from '@/stores/uiStore'

// #123: the tab signs itself out after the session's idle timeout, and only
// real user activity counts.
describe('activity tracking', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-10-27T10:00:00Z'))
    localStorage.clear()
    applySessionMeta({ idle_minutes: 10, expires_at: '2026-10-27T22:00:00Z' })
  })

  afterEach(() => {
    stopActivityTracking()
    vi.useRealTimers()
  })

  it('signs out after the idle timeout without activity', () => {
    const onIdle = vi.fn()
    startActivityTracking(onIdle)

    vi.advanceTimersByTime(9 * 60_000)
    expect(onIdle).not.toHaveBeenCalled()

    vi.advanceTimersByTime(60_000 + 15_000)
    expect(onIdle).toHaveBeenCalledTimes(1)
  })

  it('activity restarts the idle countdown', () => {
    const onIdle = vi.fn()
    startActivityTracking(onIdle)

    vi.advanceTimersByTime(8 * 60_000)
    window.dispatchEvent(new Event('keydown'))
    vi.advanceTimersByTime(8 * 60_000)

    expect(onIdle).not.toHaveBeenCalled()
  })

  it('warns a minute before signing out', () => {
    const addToast = vi.spyOn(useUIStore.getState(), 'addToast')
    startActivityTracking(vi.fn())

    vi.advanceTimersByTime(9 * 60_000 + 15_000)

    expect(addToast).toHaveBeenCalledWith(expect.stringContaining('inactivity'), 'info')
  })

  it('counts activity in another tab', () => {
    const onIdle = vi.fn()
    startActivityTracking(onIdle)

    vi.advanceTimersByTime(8 * 60_000)
    localStorage.setItem('irdoc:last-activity', String(Date.now()))
    vi.advanceTimersByTime(8 * 60_000)

    expect(onIdle).not.toHaveBeenCalled()
  })

  it('hasActivitySince only sees activity after the given time', () => {
    markActivity()
    const tokenAt = Date.now() + 1
    vi.advanceTimersByTime(5_000)

    expect(hasActivitySince(tokenAt)).toBe(false)
    markActivity()
    expect(hasActivitySince(tokenAt)).toBe(true)
  })
})
