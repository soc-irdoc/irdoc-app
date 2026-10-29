import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { AxiosError, AxiosHeaders } from 'axios'
import { AddEntryForm } from '../AddEntryForm'

// Regression (#138): the create mutation refetched the timeline before the
// attachments were uploaded, and nothing refetched it afterwards, so a new
// entry showed no attachments until a page reload or an edit+save.

const createEntry = vi.fn().mockResolvedValue({ id: 'entry-1' })
const post = vi.fn()
const invalidateQueries = vi.fn()
const addToast = vi.fn()

vi.mock('@/hooks/useTimeline', () => ({
  useCreateTimelineEntry: () => ({ mutateAsync: createEntry, isPending: false }),
}))
vi.mock('@tanstack/react-query', () => ({
  useQueryClient: () => ({ invalidateQueries }),
}))
vi.mock('@/hooks/useAssets', () => ({
  useAssets: () => ({ data: [] }),
  useLinkAssetsToEntry: () => ({ mutateAsync: vi.fn() }),
}))
vi.mock('@/stores/uiStore', () => ({
  useUIStore: (selector: (s: { addToast: typeof addToast }) => unknown) => selector({ addToast }),
}))
vi.mock('@/lib/apiClient', () => ({ default: { post } }))

function addEntryWithFiles(files: File[]) {
  const { container } = render(<AddEntryForm incidentId="incident-1" />)
  fireEvent.change(screen.getByPlaceholderText(/Describe what happened/i), { target: { value: 'x' } })
  fireEvent.change(container.querySelector('input[type="file"]') as HTMLInputElement, { target: { files } })
  fireEvent.click(screen.getByRole('button', { name: 'Add Entry' }))
}

describe('AddEntryForm attachments', () => {
  beforeEach(() => {
    post.mockReset()
    invalidateQueries.mockClear()
    addToast.mockClear()
  })

  it('refetches the timeline after the uploads finish', async () => {
    const order: string[] = []
    post.mockImplementation(async () => { order.push('upload') })
    invalidateQueries.mockImplementation(({ queryKey }: { queryKey: string[] }) => { order.push(queryKey[0]) })

    addEntryWithFiles([new File(['a'], 'a.csv'), new File(['b'], 'b.csv')])

    await vi.waitFor(() => expect(addToast).toHaveBeenCalled())
    expect(post).toHaveBeenCalledTimes(2)
    expect(order.indexOf('timeline')).toBeGreaterThan(order.lastIndexOf('upload'))
  })

  it('names the reason when an upload fails', async () => {
    post.mockRejectedValue(new AxiosError('Request failed', '413', undefined, undefined, {
      status: 413, statusText: '', headers: {}, config: { headers: new AxiosHeaders() }, data: '<html>',
    }))

    addEntryWithFiles([new File(['x'], 'security.evtx')])

    await vi.waitFor(() => expect(addToast).toHaveBeenCalled())
    const [message, kind] = addToast.mock.calls[0]
    expect(kind).toBe('error')
    expect(message).toContain('security.evtx: file too large')
    expect(message).toContain('HTTP 413')
  })
})
