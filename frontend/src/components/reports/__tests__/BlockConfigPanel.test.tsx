import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import BlockConfigPanel from '../BlockConfigPanel'
import type { ReportBlock } from '@/types/report'

// TipTap needs a real layout engine; the panel only needs to know it's mounted.
vi.mock('@/components/common/RichTextEditor', () => ({
  RichTextEditor: () => <div>RICH_TEXT_EDITOR</div>,
}))

const block = (b: Partial<ReportBlock>): ReportBlock => ({ id: 'b1', type: 'section', ...b })

describe('BlockConfigPanel', () => {
  it('offers only the incident Summary fields for a Section block', () => {
    render(<BlockConfigPanel block={block({ field: 'incident.executive_summary' })} onChange={vi.fn()} />)
    const labels = screen.getAllByRole('option').map((o) => o.textContent)
    expect(labels).toEqual(['— Select field —', 'Executive Summary', 'Notes', 'Lessons Learned', 'To-do'])
  })

  it('maps the legacy metadata.notes path onto Notes', () => {
    render(<BlockConfigPanel block={block({ field: 'incident.metadata.notes' })} onChange={vi.fn()} />)
    expect(screen.getByRole('combobox')).toHaveValue('incident.notes')
  })

  it('flags a removed field as unsupported', () => {
    render(<BlockConfigPanel block={block({ field: 'incident.metadata.root_cause' })} onChange={vi.fn()} />)
    expect(screen.getByText(/no longer available/)).toBeInTheDocument()
  })

  it('gives a Text Block an editor and no field picker', () => {
    render(<BlockConfigPanel block={block({ type: 'text_block', content: '' })} onChange={vi.fn()} />)
    expect(screen.getByText('RICH_TEXT_EDITOR')).toBeInTheDocument()
    expect(screen.queryByRole('combobox')).toBeNull()
  })

  it('offers to convert a field-bound legacy Text Block to a Section', () => {
    const onChange = vi.fn()
    render(<BlockConfigPanel block={block({ type: 'text_block', field: 'incident.executive_summary' })} onChange={onChange} />)
    fireEvent.click(screen.getByText('Convert to Section'))
    expect(onChange).toHaveBeenCalledWith({ type: 'section' })
  })

  it('exposes SHA-256 and uploader toggles on the Evidence Register', () => {
    const onChange = vi.fn()
    render(<BlockConfigPanel block={block({ type: 'evidence_register' })} onChange={onChange} />)
    const sha = screen.getByLabelText('Show SHA-256 hashes')
    expect(sha).toBeChecked()
    fireEvent.click(screen.getByLabelText('Show uploader'))
    expect(onChange).toHaveBeenCalledWith({ show_uploader: true })
  })
})
