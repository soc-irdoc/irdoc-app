import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ReportTemplateBuilder from '../ReportTemplateBuilder'

const aiState = { enabled: false, disabled: true }
vi.mock('@/hooks/useAiConfig', async (orig) => ({
  ...(await orig<typeof import('@/hooks/useAiConfig')>()),
  useAiStatus: () => aiState,
}))

describe('ReportTemplateBuilder with Local AI disabled (#68)', () => {
  it('keeps the AI block visible but disabled', () => {
    const onChange = vi.fn()
    render(<ReportTemplateBuilder blocks={[]} onChange={onChange} />)
    const add = screen.getByRole('button', { name: 'Add AI Strategy Summary' })
    expect(add).toBeDisabled()
    fireEvent.click(screen.getByText('AI Strategy Summary'))
    expect(onChange).not.toHaveBeenCalled()
    // Non-AI blocks are unaffected
    expect(screen.getByRole('button', { name: 'Add Section' })).toBeEnabled()
  })

  it('marks an already-placed AI block as disabled', () => {
    render(<ReportTemplateBuilder blocks={[{ id: 'a', type: 'ai_strategy' }]} onChange={vi.fn()} />)
    expect(screen.getByText(/Local AI \(Ollama\) is disabled/)).toBeInTheDocument()
  })

  it('enables the AI block when AI is on', () => {
    Object.assign(aiState, { enabled: true, disabled: false })
    render(<ReportTemplateBuilder blocks={[]} onChange={vi.fn()} />)
    expect(screen.getByRole('button', { name: 'Add AI Strategy Summary' })).toBeEnabled()
  })
})
