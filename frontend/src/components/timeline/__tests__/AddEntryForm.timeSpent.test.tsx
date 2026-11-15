import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { AddEntryForm } from '../AddEntryForm'

// #165: optional time spent on an entry; untouched means "not tracked".
const mutateAsync = vi.fn().mockResolvedValue({ id: 'entry-1' })

vi.mock('@/hooks/useTimeline', () => ({
  useCreateTimelineEntry: () => ({ mutateAsync, isPending: false }),
}))
vi.mock('@tanstack/react-query', () => ({
  useQueryClient: () => ({ invalidateQueries: vi.fn() }),
}))
vi.mock('@/hooks/useAssets', () => ({
  useAssets: () => ({ data: [] }),
  useLinkAssetsToEntry: () => ({ mutateAsync: vi.fn() }),
}))
vi.mock('@/hooks/useIOCs', () => ({
  useIOCs: () => ({ data: [] }),
  useSetIOCLink: () => ({ mutateAsync: vi.fn() }),
}))
vi.mock('@/stores/uiStore', () => ({
  useUIStore: (selector: (s: { addToast: () => void }) => unknown) => selector({ addToast: vi.fn() }),
}))

async function submit() {
  fireEvent.change(screen.getByPlaceholderText(/Describe what happened/i), { target: { value: 'x' } })
  fireEvent.click(screen.getByRole('button', { name: 'Add Entry' }))
  await vi.waitFor(() => expect(mutateAsync).toHaveBeenCalledTimes(1))
  return mutateAsync.mock.calls[0][0]
}

describe('AddEntryForm time spent', () => {
  beforeEach(() => mutateAsync.mockClear())

  it('sends nothing when left empty', async () => {
    render(<AddEntryForm incidentId="incident-1" />)
    expect((await submit()).time_spent_minutes).toBeUndefined()
  })

  it('sends the quick-pick value', async () => {
    render(<AddEntryForm incidentId="incident-1" />)
    fireEvent.click(screen.getByRole('button', { name: '15m' }))
    expect((await submit()).time_spent_minutes).toBe(15)
  })

  it('sends a typed value, capped at 24 hours', async () => {
    render(<AddEntryForm incidentId="incident-1" />)
    fireEvent.change(screen.getByLabelText(/Time spent/), { target: { value: '5000' } })
    expect((await submit()).time_spent_minutes).toBe(1440)
  })
})
