import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { IOCPage } from '../IOCPage'

// seed_demo.py stores IOCs of type "other", which isn't in IOCType (#112).
const iocs = [{
  id: 'ioc1', incident_id: 'i1', ioc_type: 'other', value: 'app-id: 7e2c1a9d', confidence: 80,
  status: 'active', enrichment: {}, tlp_level: 'amber', tags: [],
  created_at: '2026-10-09T10:00:00Z', updated_at: '2026-10-09T10:00:00Z',
}]
const mutation = { mutateAsync: vi.fn(), mutate: vi.fn(), isPending: false }

vi.mock('@/hooks/useIOCs', () => ({
  useIOCs: () => ({ data: iocs, isLoading: false }),
  useCreateIOC: () => mutation,
  useUpdateIOC: () => mutation,
  useDeleteIOC: () => mutation,
  useBulkImportIOCs: () => mutation,
}))
vi.mock('@/lib/websocket', () => ({ getSocket: () => ({ on: vi.fn(), off: vi.fn() }) }))

describe('IOCPage', () => {
  it('renders an IOC whose type has no icon instead of crashing (#112)', () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <IOCPage incidentId="i1" />
      </QueryClientProvider>,
    )
    expect(screen.getByText('app-id: 7e2c1a9d')).toBeTruthy()
    expect(screen.getAllByText('other').length).toBeGreaterThan(0)
  })
})
