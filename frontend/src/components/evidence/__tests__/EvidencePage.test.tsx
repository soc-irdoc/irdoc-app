import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import type { EvidenceFile } from '@/types/evidence'

const filesMock = vi.fn()
const iocsMock = vi.fn()
vi.mock('@/hooks/useEvidence', () => ({
  useEvidenceFiles: (...args: unknown[]) => filesMock(...args),
  useEvidenceIOCs: (...args: unknown[]) => iocsMock(...args),
}))
const get = vi.fn()
vi.mock('@/lib/apiClient', () => ({ default: { get: (...a: unknown[]) => get(...a) } }))

import { EvidencePage } from '../EvidencePage'

const SHA = 'ab'.repeat(32)

function file(over: Partial<EvidenceFile> = {}): EvidenceFile {
  return {
    id: 'f1', kind: 'timeline', original_name: 'dropper.bin', mime_type: 'application/octet-stream',
    file_size: 2048, sha256: SHA, is_screenshot: false, uploaded_by: 'u1', uploaded_by_name: 'Ana Analyst',
    uploaded_at: '2026-11-01T10:00:00Z',
    source: { entry_id: 'e1', entry_type: 'evidence', occurred_at: '2026-11-01T09:00:00Z', excerpt: 'Found on WS-01' },
    assets: [{ id: 'a1', name: 'WS-01', asset_type: 'workstation' }],
    ioc_matches: [{ id: 'i1', ioc_type: 'hash', value: SHA }],
    ...over,
  }
}

let location = ''
function Probe() {
  const loc = useLocation()
  location = loc.pathname + loc.search
  return null
}

function renderAt(path = '/incidents/inc1/evidence') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/incidents/:id/:section" element={<><EvidencePage incidentId="inc1" /><Probe /></>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('EvidencePage (#150)', () => {
  beforeEach(() => {
    filesMock.mockReset()
    get.mockReset()
    iocsMock.mockReturnValue({ data: [], isLoading: false, isError: false })
    filesMock.mockReturnValue({
      data: { data: [file(), file({ id: 'f2', kind: 'incident', original_name: 'memo.pdf', mime_type: 'application/pdf', source: null, assets: [], ioc_matches: [] })], meta: { total: 2 } },
      isLoading: false, isError: false,
    })
  })

  it('lists files with their source, chips and hash match', () => {
    renderAt()

    expect(screen.getByRole('heading', { name: 'Evidence Register' })).toBeInTheDocument()
    expect(screen.getAllByTestId('evidence-row')).toHaveLength(2)
    expect(screen.getByText('Found on WS-01')).toBeInTheDocument()
    expect(screen.getByText('WS-01')).toBeInTheDocument()
    expect(screen.getByText('MATCHES IOC')).toBeInTheDocument()
    const rows = screen.getAllByTestId('evidence-row')
    expect(within(rows[1]).getByText('Incident')).toBeInTheDocument()
  })

  it('has no upload or delete controls', () => {
    renderAt()
    expect(screen.queryByRole('button', { name: /^(upload|delete|remove)\b/i })).toBeNull()
    expect(document.querySelector('input[type="file"]')).toBeNull()
  })

  it('jumps to the source timeline entry and to the matched IOC', () => {
    renderAt()
    fireEvent.click(screen.getByRole('button', { name: /Evidence ·/ }))
    expect(location).toBe('/incidents/inc1/timeline?entry=e1')
  })

  it('keeps filters in the URL', async () => {
    renderAt('/incidents/inc1/evidence?type=image%2F&hide_screenshots=1')
    expect(filesMock.mock.calls.slice(-1)[0]?.[1]).toMatchObject({ type: 'image/', hideScreenshots: true })

    fireEvent.change(screen.getByLabelText('Filter by source'), { target: { value: 'incident' } })
    await waitFor(() => expect(location).toContain('kind=incident'))
  })

  it('offers no preview for unsafe or unknown types, only download and hash', async () => {
    renderAt()
    fireEvent.click(screen.getByRole('button', { name: 'Preview dropper.bin' }))

    expect(await screen.findByText(/Preview not available for this file type/)).toBeInTheDocument()
    expect(screen.getByText(SHA)).toBeInTheDocument()
    expect(get).not.toHaveBeenCalled()
  })

  it('shows the empty state', () => {
    filesMock.mockReturnValue({ data: { data: [], meta: { total: 0 } }, isLoading: false, isError: false })
    renderAt()
    expect(screen.getByText('Files added to timeline entries appear here.')).toBeInTheDocument()
  })
})
