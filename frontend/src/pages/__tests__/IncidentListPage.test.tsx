import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// #126-#128: the list is paged and sorted on the server, from URL state.
const useIncidentsMock = vi.fn()

vi.mock('@/hooks/useIncident', () => ({
  useIncidents: (params: unknown) => useIncidentsMock(params),
  useCreateIncident: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useIncidentTemplates: () => ({ data: [] }),
  useUpdateIncident: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useDeleteIncident: () => ({ mutateAsync: vi.fn(), isPending: false }),
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
  return useIncidentsMock.mock.calls.at(-1)?.[0]
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
})
