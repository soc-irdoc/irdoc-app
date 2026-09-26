import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, act } from '@testing-library/react'
import { AddEntryForm } from '../AddEntryForm'

// Regression (#65): a 1s interval kept overwriting the time field while the
// form was focused, so a specific hour could never be entered.

const mutateAsync = vi.fn().mockResolvedValue({ id: 'entry-1' })

vi.mock('@/hooks/useTimeline', () => ({
  useCreateTimelineEntry: () => ({ mutateAsync, isPending: false }),
}))
vi.mock('@/hooks/useAssets', () => ({
  useAssets: () => ({ data: [] }),
  useLinkAssetsToEntry: () => ({ mutateAsync: vi.fn() }),
}))
vi.mock('@/stores/uiStore', () => ({
  useUIStore: (selector: (s: { addToast: () => void }) => unknown) =>
    selector({ addToast: vi.fn() }),
}))

function setup() {
  const { container } = render(<AddEntryForm incidentId="incident-1" />)
  const form = container.querySelector('form') as HTMLFormElement
  const date = container.querySelector('input[type="date"]') as HTMLInputElement
  const time = container.querySelector('input[type="time"]') as HTMLInputElement
  fireEvent.focus(form)
  return { date, time }
}

async function submit() {
  fireEvent.change(screen.getByPlaceholderText(/Describe what happened/i), { target: { value: 'x' } })
  fireEvent.click(screen.getByRole('button', { name: 'Add Entry' }))
  await vi.waitFor(() => expect(mutateAsync).toHaveBeenCalledTimes(1))
  return mutateAsync.mock.calls[0][0].occurred_at as string
}

describe('AddEntryForm live time', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    vi.setSystemTime(new Date('2026-09-26T10:00:00'))
    mutateAsync.mockClear()
  })
  afterEach(() => vi.useRealTimers())

  it('follows the clock while untouched', () => {
    const { time } = setup()
    expect(time.value).toBe('10:00:00')
    act(() => { vi.advanceTimersByTime(3000) })
    expect(time.value).toBe('10:00:03')
    expect(screen.getByRole('button', { name: /Live/ })).toBeDisabled()
  })

  it('keeps a manually entered time instead of overwriting it', async () => {
    const { time } = setup()
    fireEvent.change(time, { target: { value: '08:15:00' } })
    act(() => { vi.advanceTimersByTime(5000) })
    expect(time.value).toBe('08:15:00')
    expect(await submit()).toBe(new Date('2026-09-26T08:15:00').toISOString())
  })

  it('keeps a manually chosen date', () => {
    const { date } = setup()
    fireEvent.change(date, { target: { value: '2026-09-20' } })
    act(() => { vi.advanceTimersByTime(5000) })
    expect(date.value).toBe('2026-09-20')
  })

  it('"Now" resumes following the clock', () => {
    const { time } = setup()
    fireEvent.change(time, { target: { value: '08:15:00' } })
    fireEvent.click(screen.getByRole('button', { name: 'Now' }))
    act(() => { vi.advanceTimersByTime(2000) })
    expect(time.value).not.toBe('08:15:00')
    expect(screen.getByRole('button', { name: /Live/ })).toBeDisabled()
  })

  it('uses the submit instant in live mode', async () => {
    setup()
    vi.setSystemTime(new Date('2026-09-26T10:00:07.500'))
    expect(await submit()).toBe(new Date('2026-09-26T10:00:07.500').toISOString())
  })
})
