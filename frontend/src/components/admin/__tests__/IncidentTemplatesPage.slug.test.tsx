import { describe, expect, it, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AxiosError, AxiosHeaders } from 'axios'

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() }))
vi.mock('@/lib/apiClient', () => ({ default: api }))

import { IncidentTemplatesPage } from '../IncidentTemplatesPage'

function httpError(status: number, data: unknown) {
  const config = { headers: new AxiosHeaders() }
  return new AxiosError('fail', 'ERR', config, null, { status, statusText: '', headers: {}, config, data })
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <IncidentTemplatesPage />
    </QueryClientProvider>,
  )
}

const mine = {
  id: 't1', org_id: 'o1', name: 'Phishing (Copy)', slug: 'phishing-copy', description: null,
  is_system: false, is_hidden: false, tasks_json: [], created_at: '2026-11-14T10:00:00Z',
}

beforeEach(() => {
  vi.clearAllMocks()
  api.get.mockResolvedValue({ data: { data: [mine], error: null } })
})

// #168 / #169: slug conflicts and format errors show next to the slug field.
describe('IncidentTemplatesPage slug', () => {
  it('generates a clean slug from the name', async () => {
    renderPage()
    fireEvent.click(await screen.findByText('+ New Template'))
    fireEvent.change(screen.getByPlaceholderText('e.g. Ransomware Response'), {
      target: { value: '  Phish & Spam -- Finance! ' },
    })
    expect(screen.getByPlaceholderText('ransomware-response')).toHaveValue('phish-spam-finance')
  })

  it('shows a 409 from the server inline on the slug field', async () => {
    api.post.mockRejectedValue(httpError(409, { detail: "Slug 'phish' is already used by template 'Phishing'" }))
    renderPage()
    fireEvent.click(await screen.findByText('+ New Template'))
    fireEvent.change(screen.getByPlaceholderText('e.g. Ransomware Response'), { target: { value: 'Phish' } })
    fireEvent.click(screen.getByText('Save Template'))

    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent("Slug 'phish' is already used by template 'Phishing'"),
    )
    expect(screen.getByPlaceholderText('ransomware-response')).toHaveAttribute('aria-invalid', 'true')
  })

  it('warns that renaming the slug breaks API callers using the old one', async () => {
    renderPage()
    const edit = await screen.findAllByText('Edit')
    fireEvent.click(edit[0])
    fireEvent.change(screen.getByPlaceholderText('ransomware-response'), { target: { value: 'phishing-finance' } })
    expect(screen.getByText(/will stop matching this template/)).toHaveTextContent('phishing-copy')
  })
})
