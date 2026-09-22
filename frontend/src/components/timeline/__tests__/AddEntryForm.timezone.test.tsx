import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { AddEntryForm } from '../AddEntryForm'

// Regression test for: a timeline entry saved as 19:57:03 local time displayed
// back as 22:57:0x — a 3-hour shift matching this machine's UTC+3 offset.
//
// Root cause: AddEntryForm built `occurred_at` as a naive `${date}T${time}`
// string with no timezone offset (unlike EditEntryModal, which correctly does
// `new Date(...).toISOString()`). The backend's timestamptz column assumes a
// naive datetime is UTC, so the local wall-clock time got stored as if it were
// UTC, and was then correctly converted UTC→local for display — silently
// adding the offset a second time on every read.

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

describe('AddEntryForm timezone handling', () => {
  beforeEach(() => {
    // A fixed positive offset (UTC+3, matching Europe/Chisinau in September)
    // so a bug that skips UTC conversion produces a detectable, non-zero shift.
    vi.stubEnv('TZ', 'Europe/Chisinau')
    mutateAsync.mockClear()
  })
  afterEach(() => vi.unstubAllEnvs())

  it('sends occurred_at as a UTC instant, not a naive local string', async () => {
    const { container } = render(<AddEntryForm incidentId="incident-1" />)

    // The date/time <label>s aren't associated to their <input>s (no
    // htmlFor/id), so they aren't reachable via getByLabelText — select by
    // input type instead.
    const dateInput = container.querySelector('input[type="date"]') as HTMLInputElement
    const timeInput = container.querySelector('input[type="time"]') as HTMLInputElement
    fireEvent.change(dateInput, { target: { value: '2026-09-22' } })
    fireEvent.change(timeInput, { target: { value: '19:57:03' } })
    fireEvent.change(screen.getByPlaceholderText(/Describe what happened/i), {
      target: { value: 'Test entry' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Add Entry' }))

    await vi.waitFor(() => expect(mutateAsync).toHaveBeenCalledTimes(1))

    const { occurred_at } = mutateAsync.mock.calls[0][0]

    // Must be an absolute instant (parseable with a UTC offset), not a naive
    // local-time string with no timezone information.
    expect(occurred_at).toBe(new Date('2026-09-22T19:57:03').toISOString())
    expect(occurred_at).not.toBe('2026-09-22T19:57:03')
  })
})
