import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'

// #152: an IOC row lists the timeline entries it was seen in, and toggles links.
const setLink = vi.hoisted(() => vi.fn())
const iocs = [{
  id: 'ioc1', incident_id: 'i1', ioc_type: 'domain', value: 'evil.example.com', confidence: 80,
  status: 'active', enrichment: {}, tlp_level: 'amber', tags: [],
  created_at: '2026-11-14T10:00:00Z', updated_at: '2026-11-14T10:00:00Z',
}]
const entries = [
  { id: 'e1', incident_id: 'i1', entry_type: 'detection', occurred_at: '2026-11-14T09:00:00Z',
    description: '<p>Alert on <b>evil.example.com</b></p>', attachments: [] },
  { id: 'e2', incident_id: 'i1', entry_type: 'analysis', occurred_at: '2026-11-14T09:30:00Z',
    description: '<p>Proxy logs reviewed</p>', attachments: [] },
]
const mutation = { mutateAsync: vi.fn(), mutate: vi.fn(), isPending: false }

vi.mock('@/hooks/useIOCs', () => ({
  useIOCs: () => ({ data: iocs, isLoading: false }),
  useCreateIOC: () => mutation,
  useUpdateIOC: () => mutation,
  useDeleteIOC: () => mutation,
  useBulkImportIOCs: () => mutation,
  useIOCLinks: () => ({ data: [{ ioc_id: 'ioc1', timeline_entry_id: 'e1' }] }),
  useSetIOCLink: () => ({ mutateAsync: setLink, isPending: false }),
}))
vi.mock('@/hooks/useTimeline', () => ({ useTimeline: () => ({ data: entries }) }))
vi.mock('@/lib/websocket', () => ({ getSocket: () => ({ on: vi.fn(), off: vi.fn() }) }))
vi.mock('@/lib/permissions', () => ({ usePermission: () => true }))

import { IOCPage } from '../IOCPage'

function renderPage() {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <IOCPage incidentId="i1" />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('IOCPage entry links', () => {
  beforeEach(() => setLink.mockReset().mockResolvedValue(undefined))

  it('marks IOCs that were seen in entries', () => {
    renderPage()
    expect(screen.getByTitle(/Timeline entries this IOC was seen in/)).toHaveTextContent('SEEN IN 1')
  })

  it('lists the entries and toggles links from the expanded row', () => {
    renderPage()
    fireEvent.click(screen.getByText('evil.example.com').closest('tr')!)

    const detection = screen.getByRole('checkbox', { name: /Seen in Detection entry/ })
    const analysis = screen.getByRole('checkbox', { name: /Seen in Analysis entry/ })
    expect(detection).toBeChecked()
    expect(analysis).not.toBeChecked()
    expect(screen.getByText('Alert on evil.example.com')).toBeInTheDocument() // HTML shown as text

    fireEvent.click(analysis)
    expect(setLink).toHaveBeenCalledWith({ iocId: 'ioc1', entryId: 'e2', linked: true })
    fireEvent.click(detection)
    expect(setLink).toHaveBeenCalledWith({ iocId: 'ioc1', entryId: 'e1', linked: false })
  })
})
