import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// #126-#128: the list is paged and sorted on the server, from URL state.
const useIncidentsMock = vi.fn()
const createMock = vi.fn()
const bulkMock = vi.fn()

vi.mock('@/hooks/useIncident', () => ({
  useIncidents: (params: unknown) => useIncidentsMock(params),
  useCreateIncident: () => ({ mutateAsync: createMock, isPending: false }),
  useIncidentTemplates: () => ({ data: [] }),
  useUpdateIncident: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useDeleteIncident: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useBulkSetSource: () => ({ mutateAsync: bulkMock, isPending: false }),
}))
vi.mock('@/components/layout/AppShell', () => ({
  AppShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))
vi.mock('@/lib/permissions', () => ({ usePermission: () => true }))

import { IncidentListPage } from '@/pages/IncidentListPage'

function incident(n: number) {
  return {
    id: `id-${n}`,
    org_id: 'o',
    incident_ref: `INC-2026-${String(n).padStart(4, '0')}`,
    title: `Incident ${n}`,
    severity: 'high',
    status: 'open',
    disposition: null,
    source: 'siem_alert',
    assigned_to: null,
    assigned_user: null,
    external_refs: [],
    created_at: '2026-10-27T10:00:00Z',
  }
}

let location = ''
function LocationProbe() {
  const loc = useLocation()
  location = loc.search
  return null
}

function renderAt(path: string) {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/incidents" element={<><IncidentListPage /><LocationProbe /></>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

function lastParams() {
  const calls = useIncidentsMock.mock.calls
  return calls[calls.length - 1]?.[0]
}

describe('IncidentListPage', () => {
  beforeEach(() => {
    useIncidentsMock.mockReset()
    useIncidentsMock.mockReturnValue({
      data: { data: [incident(26), incident(27)], meta: { page: 2, per_page: 25, total: 132 } },
      isLoading: false,
      isFetching: false,
    })
  })

  it('requests the page, filter, search and sort from the URL', () => {
    renderAt('/incidents?page=2&status=open&q=phish&sort=severity&order=desc')

    expect(lastParams()).toEqual({
      status: 'open', search: 'phish', page: 2, per_page: 25, sort: 'severity', order: 'desc',
    })
    expect(screen.getByText('Showing 26 to 50 of 132')).toBeInTheDocument()
  })

  it('changing the filter goes back to page 1', async () => {
    renderAt('/incidents?page=2')

    fireEvent.click(screen.getByRole('button', { name: 'Closed' }))

    await waitFor(() => expect(lastParams()).toMatchObject({ status: 'closed', page: 1 }))
    expect(location).toBe('?status=closed')
  })

  it('page buttons change only the page', async () => {
    renderAt('/incidents?page=2&sort=title&order=asc')

    fireEvent.click(screen.getByRole('button', { name: 'Next page' }))

    await waitFor(() => expect(lastParams()).toMatchObject({ page: 3, sort: 'title', order: 'asc' }))
  })

  it('clicking a header sorts by it, and again reverses it', async () => {
    renderAt('/incidents')

    fireEvent.click(screen.getByRole('button', { name: 'Sort by title' }))
    await waitFor(() => expect(lastParams()).toMatchObject({ sort: 'title', order: 'asc', page: 1 }))

    fireEvent.click(screen.getByRole('button', { name: /Title, sorted ascending/ }))
    await waitFor(() => expect(lastParams()).toMatchObject({ sort: 'title', order: 'desc' }))
  })

  it('shows the source of each incident, and NO SOURCE when none was recorded (#171)', () => {
    useIncidentsMock.mockReturnValue({
      data: { data: [incident(1), { ...incident(2), source: null }], meta: { page: 1, per_page: 25, total: 2 } },
      isLoading: false,
      isFetching: false,
    })
    renderAt('/incidents')
    expect(screen.getByTitle('SIEM Alert')).toHaveTextContent('SIEM')
    expect(screen.getAllByText('NO SOURCE')).toHaveLength(1)
  })

  it('sorts by source (#171)', async () => {
    renderAt('/incidents')
    fireEvent.click(screen.getByRole('button', { name: 'Sort by source' }))
    await waitFor(() => expect(lastParams()).toMatchObject({ sort: 'source', order: 'asc', page: 1 }))
  })

  it('bulk-sets the source on selected incidents, only where none was recorded (#153)', async () => {
    useIncidentsMock.mockReturnValue({
      data: {
        data: [{ ...incident(1), source: null }, incident(2), { ...incident(3), source: null }],
        meta: { page: 1, per_page: 25, total: 3 },
      },
      isLoading: false,
      isFetching: false,
    })
    bulkMock.mockResolvedValue({ updated: 2, skipped: 1, not_found: 0 })
    renderAt('/incidents')

    fireEvent.click(screen.getByLabelText('Select all incidents on this page'))
    expect(screen.getByRole('region', { name: 'Bulk actions' })).toHaveTextContent('3 selected')

    fireEvent.click(screen.getByRole('button', { name: /Set source/ }))
    fireEvent.change(document.getElementById('bulk-source')!, { target: { value: 'siem_alert' } })
    expect(screen.getByRole('status')).toHaveTextContent('2 incidents will be set to SIEM Alert.')
    expect(screen.getByRole('status')).toHaveTextContent('1 already have a source')

    const dialogButtons = screen.getAllByRole('button', { name: 'Set source' })
    fireEvent.click(dialogButtons[dialogButtons.length - 1])
    await waitFor(() => expect(bulkMock).toHaveBeenCalledWith({
      ids: ['id-1', 'id-2', 'id-3'], source: 'siem_alert', overwrite: false,
    }))
  })

  it('clicking a row checkbox selects it without opening the incident (#153)', () => {
    renderAt('/incidents')
    fireEvent.click(screen.getByLabelText('Select INC-2026-0026'))
    expect(screen.getByRole('region', { name: 'Bulk actions' })).toHaveTextContent('1 selected')
    expect(location).toBe('')
  })

  it('severity sorts most severe first on the first click', async () => {
    renderAt('/incidents')

    fireEvent.click(screen.getByRole('button', { name: 'Sort by severity' }))

    await waitFor(() => expect(lastParams()).toMatchObject({ sort: 'severity', order: 'desc' }))
  })

  it('changing the page size goes back to page 1', async () => {
    renderAt('/incidents?page=3')

    fireEvent.change(screen.getByRole('combobox', { name: 'Per page' }), { target: { value: '100' } })

    await waitFor(() => expect(lastParams()).toMatchObject({ per_page: 100, page: 1 }))
  })

  // #147: every new incident records what triggered it.
  it('needs a source before an incident can be created', async () => {
    createMock.mockResolvedValue({ id: 'new' })
    renderAt('/incidents')

    fireEvent.click(screen.getByRole('button', { name: /new incident/i }))
    fireEvent.change(screen.getByPlaceholderText(/phishing campaign/i), { target: { value: 'Odd login' } })
    const create = screen.getByRole('button', { name: 'Create Incident' })
    expect(create).toBeDisabled()

    fireEvent.change(screen.getByLabelText('Source'), { target: { value: 'cloud_alert' } })
    fireEvent.click(create)

    await waitFor(() => expect(createMock).toHaveBeenCalledWith(
      expect.objectContaining({ title: 'Odd login', source: 'cloud_alert' }),
    ))
  })

  it('filters by source, including incidents with none recorded', async () => {
    renderAt('/incidents')

    fireEvent.change(screen.getByLabelText('Filter by source'), { target: { value: 'none' } })

    await waitFor(() => expect(lastParams()).toMatchObject({ source: 'none', page: 1 }))
    expect(location).toContain('source=none')
  })
})
