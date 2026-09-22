import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { Incident } from '@/types/incident'

// Stub every tab-content component with a trivial marker so we isolate the
// tab-switching mechanism in IncidentWorkspacePage/TopBar from whatever each
// real tab does internally (data fetching, sockets, etc).
vi.mock('@/components/timeline/TimelinePage', () => ({ TimelinePage: () => <div>TIMELINE_CONTENT</div> }))
vi.mock('@/components/ioc/IOCPage', () => ({ IOCPage: () => <div>IOCS_CONTENT</div> }))
vi.mock('@/components/assets/AssetsPage', () => ({ AssetsPage: () => <div>ASSETS_CONTENT</div> }))
vi.mock('@/components/summary/SummaryPage', () => ({ SummaryPage: () => <div>SUMMARY_CONTENT</div> }))
vi.mock('@/components/reports/ReportPage', () => ({ default: () => <div>REPORTS_CONTENT</div> }))
vi.mock('@/components/graph/InvestigationGraph', () => ({ default: () => <div>GRAPH_CONTENT</div> }))
vi.mock('@/components/layout/TasksPanel', () => ({ TasksPanel: () => <div>TASKS_PANEL</div> }))
vi.mock('@/components/layout/LeftNav', () => ({ LeftNav: () => <div>LEFT_NAV</div> }))

// Avoid real websocket connections.
vi.mock('@/lib/websocket', () => ({
  joinIncident: vi.fn(),
  leaveIncident: vi.fn(),
}))

const mockIncident: Incident = {
  id: '64ca4067-f783-47fb-815e-4199636091cc',
  org_id: 'org-1',
  incident_ref: 'INC-0001',
  title: 'Test incident',
  severity: 'sev2',
  status: 'open',
  assigned_to: null,
  assigned_user: null,
  executive_summary: null,
  notes: null,
  lessons_learned: null,
  actions_todo: null,
  attack_vector: [],
  affected_users: 0,
  metadata: {},
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  contained_at: null,
  closed_at: null,
  external_refs: [],
}

// Mock the data hooks used by IncidentWorkspacePage/TopBar so no real network
// call is required.
vi.mock('@/hooks/useIncident', () => ({
  useIncident: () => ({ data: mockIncident, isLoading: false }),
  useUpdateIncident: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useDeleteIncident: () => ({ mutateAsync: vi.fn(), isPending: false }),
}))
vi.mock('@/hooks/useOrgUsers', () => ({
  useOrgUsers: () => ({ data: [] }),
}))
vi.mock('@/lib/permissions', () => ({
  usePermission: () => true,
}))

import { IncidentWorkspacePage } from '@/pages/IncidentWorkspacePage'

function renderAt(initialPath: string) {
  const queryClient = new QueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route path="/incidents/:id" element={<IncidentWorkspacePage />} />
          <Route path="/incidents/:id/:section" element={<IncidentWorkspacePage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('IncidentWorkspacePage tab switching', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('switches tab content when clicking Assets after landing on Timeline', async () => {
    renderAt('/incidents/64ca4067-f783-47fb-815e-4199636091cc/timeline')

    expect(screen.getByText('TIMELINE_CONTENT')).toBeInTheDocument()
    expect(screen.queryByText('ASSETS_CONTENT')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /Assets/i }))

    await waitFor(() => {
      expect(screen.getByText('ASSETS_CONTENT')).toBeInTheDocument()
    })
    expect(screen.queryByText('TIMELINE_CONTENT')).not.toBeInTheDocument()
  })

  it('switches tab content when clicking Reports after landing on Timeline', async () => {
    renderAt('/incidents/64ca4067-f783-47fb-815e-4199636091cc/timeline')

    fireEvent.click(screen.getByRole('button', { name: /Reports/i }))

    await waitFor(() => {
      expect(screen.getByText('REPORTS_CONTENT')).toBeInTheDocument()
    })
  })

  it('keeps switching correctly across multiple consecutive tab clicks', async () => {
    renderAt('/incidents/64ca4067-f783-47fb-815e-4199636091cc/timeline')

    fireEvent.click(screen.getByRole('button', { name: /Assets/i }))
    await waitFor(() => expect(screen.getByText('ASSETS_CONTENT')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: /Reports/i }))
    await waitFor(() => expect(screen.getByText('REPORTS_CONTENT')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: /IOCs/i }))
    await waitFor(() => expect(screen.getByText('IOCS_CONTENT')).toBeInTheDocument())
  })
})
