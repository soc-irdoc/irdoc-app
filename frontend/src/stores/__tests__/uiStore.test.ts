import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MAX_TOASTS, useUIStore } from '@/stores/uiStore'

const toasts = () => useUIStore.getState().toasts
const add = (...args: Parameters<ReturnType<typeof useUIStore.getState>['addToast']>) =>
  useUIStore.getState().addToast(...args)

describe('uiStore toasts', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    useUIStore.setState({ toasts: [] })
  })
  afterEach(() => vi.useRealTimers())

  it('keeps error toasts until they are dismissed (#139)', () => {
    add('upload failed (HTTP 413)', 'error')
    vi.advanceTimersByTime(60_000)
    expect(toasts()).toHaveLength(1)

    useUIStore.getState().removeToast(toasts()[0].id)
    expect(toasts()).toHaveLength(0)
  })

  it('auto-dismisses success and info toasts after 4 seconds', () => {
    add('saved', 'success')
    add('heads up')
    vi.advanceTimersByTime(3999)
    expect(toasts()).toHaveLength(2)
    vi.advanceTimersByTime(1)
    expect(toasts()).toHaveLength(0)
  })

  it('honours an explicit duration, including on errors', () => {
    add('transient error', 'error', { duration: 1000 })
    vi.advanceTimersByTime(1000)
    expect(toasts()).toHaveLength(0)
  })

  it('replaces an identical message instead of stacking it', () => {
    add('same', 'error')
    add('same', 'error')
    expect(toasts()).toHaveLength(1)
  })

  it(`caps the stack at ${MAX_TOASTS}, dropping the oldest`, () => {
    for (let i = 0; i < MAX_TOASTS + 2; i++) add(`error ${i}`, 'error')
    expect(toasts()).toHaveLength(MAX_TOASTS)
    expect(toasts()[0].message).toBe('error 2')
  })
})
