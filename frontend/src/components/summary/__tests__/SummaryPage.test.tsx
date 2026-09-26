import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { SummaryPage } from '../SummaryPage'

const incident = {
  id: 'i1', incident_ref: 'INC-2026-0002', title: 'T', severity: 'sev2', status: 'monitoring',
  executive_summary: '', notes: '', lessons_learned: '', actions_todo: '',
  ai_summary: null, ai_recommendations: null, attack_vector: [], affected_users: 0,
  opened_at: '2026-09-26T10:00:00Z', created_at: '2026-09-26T10:00:00Z', updated_at: '2026-09-26T10:00:00Z',
}
const aiState = { enabled: false, disabled: true }

vi.mock('@/hooks/useIncident', () => ({
  useIncident: () => ({ data: incident, isLoading: false }),
  useUpdateIncident: () => ({ mutateAsync: vi.fn(), mutate: vi.fn() }),
}))
vi.mock('@/hooks/useAiConfig', async (orig) => ({
  ...(await orig<typeof import('@/hooks/useAiConfig')>()),
  useAiStatus: () => aiState,
}))
vi.mock('@/components/common/RichTextEditor', () => ({ RichTextEditor: () => <div /> }))
vi.mock('@/lib/websocket', () => ({ getSocket: () => ({ on: vi.fn(), off: vi.fn() }) }))

function renderPage() {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <SummaryPage incidentId="i1" />
    </QueryClientProvider>,
  )
}

describe('SummaryPage', () => {
  beforeEach(() => Object.assign(aiState, { enabled: false, disabled: true }))

  it('colours severity and status cards by value on a single line (#66)', () => {
    renderPage()
    const sev = within(screen.getByTestId('stat-severity')).getByText('SEV-2')
    const status = within(screen.getByTestId('stat-status')).getByText('MONITORING')
    expect(sev.style.color).toBe('var(--yellow)')
    expect(sev.style.fontSize).toBe('18px')
    expect(sev.style.whiteSpace).toBe('nowrap')
    expect(status.style.color).toBe('var(--blue)')
    expect(screen.getByTestId('stat-severity').style.borderTop).toContain('var(--yellow)')
  })

  it('greys out AI cards and their Generate buttons when AI is disabled (#68)', () => {
    renderPage()
    for (const label of ['AI Summary', 'AI Recommendations']) {
      const card = screen.getByTestId(`ai-section-${label}`)
      expect(card).toHaveAttribute('aria-disabled', 'true')
      expect(within(card).getByRole('button', { name: 'Generate' })).toBeDisabled()
      expect(within(card).getByText(/Local AI \(Ollama\) is disabled/)).toBeInTheDocument()
    }
  })

  it('enables AI cards when AI is on', () => {
    Object.assign(aiState, { enabled: true, disabled: false })
    renderPage()
    const card = screen.getByTestId('ai-section-AI Summary')
    expect(within(card).getByRole('button', { name: 'Generate' })).toBeEnabled()
  })
})
