import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { EditableTitle } from '../EditableTitle'

// #125: an incident can be renamed from the workspace header.
describe('EditableTitle', () => {
  it('saves the trimmed title on Enter', async () => {
    const onSave = vi.fn().mockResolvedValue(undefined)
    render(<EditableTitle title="Phising campaign" canEdit onSave={onSave} />)

    fireEvent.click(screen.getByRole('button', { name: 'Rename incident' }))
    const input = screen.getByRole('textbox', { name: 'Incident title' })
    fireEvent.change(input, { target: { value: '  Phishing campaign ' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    fireEvent.blur(input)

    await waitFor(() => expect(onSave).toHaveBeenCalledTimes(1))
    expect(onSave).toHaveBeenCalledWith('Phishing campaign')
  })

  it('Escape cancels without saving', () => {
    const onSave = vi.fn()
    render(<EditableTitle title="Original" canEdit onSave={onSave} />)

    fireEvent.click(screen.getByRole('heading', { name: 'Original' }))
    const input = screen.getByRole('textbox', { name: 'Incident title' })
    fireEvent.change(input, { target: { value: 'Changed' } })
    fireEvent.keyDown(input, { key: 'Escape' })

    expect(onSave).not.toHaveBeenCalled()
    expect(screen.getByRole('heading', { name: 'Original' })).toBeInTheDocument()
  })

  it('does not save a blank title', () => {
    const onSave = vi.fn()
    render(<EditableTitle title="Original" canEdit onSave={onSave} />)

    fireEvent.click(screen.getByRole('heading', { name: 'Original' }))
    const input = screen.getByRole('textbox', { name: 'Incident title' })
    fireEvent.change(input, { target: { value: '   ' } })
    fireEvent.blur(input)

    expect(onSave).not.toHaveBeenCalled()
    expect(screen.getByRole('heading', { name: 'Original' })).toBeInTheDocument()
  })

  it('keeps the editor open when saving fails', async () => {
    const onSave = vi.fn().mockRejectedValue(new Error('nope'))
    render(<EditableTitle title="Original" canEdit onSave={onSave} />)

    fireEvent.click(screen.getByRole('heading', { name: 'Original' }))
    const input = screen.getByRole('textbox', { name: 'Incident title' })
    fireEvent.change(input, { target: { value: 'New' } })
    fireEvent.keyDown(input, { key: 'Enter' })

    await waitFor(() => expect(onSave).toHaveBeenCalled())
    expect(screen.getByRole('textbox', { name: 'Incident title' })).toBeInTheDocument()
  })

  it('viewers cannot rename', () => {
    render(<EditableTitle title="Read only" canEdit={false} onSave={vi.fn()} />)

    fireEvent.click(screen.getByRole('heading', { name: 'Read only' }))

    expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Rename incident' })).not.toBeInTheDocument()
  })
})
