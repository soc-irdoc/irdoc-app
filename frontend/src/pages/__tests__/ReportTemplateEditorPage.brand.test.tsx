import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, act } from '@testing-library/react'
import type { ReportBlock } from '@/types/report'
import ReportTemplateEditorPage from '../ReportTemplateEditorPage'

// Regression (#142): changing the brand colour auto-saves the template, the
// save refetches it, and the refetch re-hydrated the editor - replacing the
// unsaved layout with the last saved one.

const saved = {
  id: 'tpl-1', name: 'My template', destination: 'custom', schema_json: [],
  primary_colour: '#F97316', company_name: '', logo_data_uri: null,
}
let remote = { ...saved }
const mutate = vi.fn()

vi.mock('react-router-dom', () => ({
  useParams: () => ({ id: 'tpl-1' }),
  useNavigate: () => vi.fn(),
}))
vi.mock('@/components/layout/AppShell', () => ({
  AppShell: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))
vi.mock('@/hooks/useReportTemplates', () => ({
  useReportTemplate: () => ({ data: remote, isLoading: false }),
  useCreateReportTemplate: () => ({ mutateAsync: vi.fn() }),
  useUpdateReportTemplate: () => ({ mutate, mutateAsync: vi.fn() }),
  useUploadTemplateLogo: () => ({ mutateAsync: vi.fn(), isPending: false }),
}))
vi.mock('@/components/reports/ReportTemplateBuilder', () => ({
  default: ({ blocks, onChange }: { blocks: ReportBlock[]; onChange: (b: ReportBlock[]) => void }) => (
    <button onClick={() => onChange([...blocks, { id: `b${blocks.length}`, type: 'cover' }])}>add block</button>
  ),
}))

describe('ReportTemplateEditorPage brand auto-save', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    remote = { ...saved }
    mutate.mockClear()
  })

  it('keeps unsaved blocks when a colour change is saved and refetched', () => {
    const { rerender, container } = render(<ReportTemplateEditorPage />)
    fireEvent.click(screen.getByText('add block'))
    fireEvent.click(screen.getByText('add block'))
    fireEvent.click(screen.getByText('add block'))
    expect(screen.getByText('3 blocks')).toBeInTheDocument()

    fireEvent.change(container.querySelector('input[type="color"]') as HTMLInputElement, { target: { value: '#112233' } })
    act(() => { vi.advanceTimersByTime(700) })
    expect(mutate).toHaveBeenCalledWith({ primary_colour: '#112233' })

    // The save's refetch hands back a new object for the same template
    remote = { ...saved, primary_colour: '#112233' }
    rerender(<ReportTemplateEditorPage />)

    expect(screen.getByText('3 blocks')).toBeInTheDocument()
  })

  it('saves colour and company name together when changed in quick succession', () => {
    const { container } = render(<ReportTemplateEditorPage />)
    fireEvent.change(container.querySelector('input[type="color"]') as HTMLInputElement, { target: { value: '#112233' } })
    fireEvent.change(screen.getByPlaceholderText('Company name'), { target: { value: 'Acme' } })
    act(() => { vi.advanceTimersByTime(900) })
    expect(mutate).toHaveBeenCalledTimes(1)
    expect(mutate).toHaveBeenCalledWith({ primary_colour: '#112233', company_name: 'Acme' })
  })
})
