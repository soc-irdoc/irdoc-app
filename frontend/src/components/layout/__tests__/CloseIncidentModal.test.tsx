import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { CloseIncidentModal } from '../CloseIncidentModal'

// #124: closing an incident asks for its final disposition.
describe('CloseIncidentModal', () => {
  it('needs a choice before closing', () => {
    const onConfirm = vi.fn()
    render(<CloseIncidentModal open incidentRef="INC-2026-0001" onConfirm={onConfirm} onClose={vi.fn()} />)

    const close = screen.getByRole('button', { name: 'Close incident' })
    expect(close).toBeDisabled()

    fireEvent.click(screen.getByLabelText('False Positive - Tuning Required'))
    expect(close).toBeEnabled()
    fireEvent.click(close)

    expect(onConfirm).toHaveBeenCalledWith('fp_tuning_required')
  })

  it('offers all six dispositions', () => {
    render(<CloseIncidentModal open incidentRef="INC-2026-0001" onConfirm={vi.fn()} onClose={vi.fn()} />)

    expect(screen.getAllByRole('radio')).toHaveLength(6)
  })

  it('cancel closes without confirming', () => {
    const onConfirm = vi.fn()
    const onClose = vi.fn()
    render(<CloseIncidentModal open incidentRef="INC-2026-0001" onConfirm={onConfirm} onClose={onClose} />)

    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(onClose).toHaveBeenCalled()
    expect(onConfirm).not.toHaveBeenCalled()
  })
})
