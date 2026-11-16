import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import type { SSOConfig } from '@/types/admin'

const addToast = vi.fn()
vi.mock('@/stores/uiStore', () => ({
  useUIStore: (sel: (s: { addToast: typeof addToast }) => unknown) => sel({ addToast }),
}))

let config: SSOConfig | null = null
const save = vi.fn()
const test = vi.fn()
vi.mock('@/hooks/useAdmin', () => ({
  useSSOConfig: () => ({ data: config, isLoading: false }),
  useUpdateSSOConfig: () => ({ mutateAsync: save, isPending: false }),
  useTestSSOConnection: () => ({ mutateAsync: test, isPending: false }),
}))
vi.mock('@/hooks/useIntegrations', () => ({
  useIntegrations: () => ({ data: [] }),
  useSaveIntegrationConfig: () => ({}),
  useTestIntegration: () => ({}),
  useToggleIntegration: () => ({}),
}))

import { IdentitySection } from '../IntegrationsPage'

const TENANT = '55555555-5555-5555-5555-555555555555'
const CLIENT = '66666666-6666-6666-6666-666666666666'

function renderSection() {
  return render(<MemoryRouter><IdentitySection autoExpand /></MemoryRouter>)
}

const toggle = (c: HTMLElement) => c.querySelector('.toggle-switch input') as HTMLInputElement
const secret = () => screen.getByLabelText('Client Secret')
const saveBtn = () => screen.getByRole('button', { name: 'Save SSO Configuration' })
const testBtn = () => screen.getByRole('button', { name: 'Test connection' })

describe('IdentitySection SSO rules', () => {
  beforeEach(() => {
    addToast.mockReset()
    save.mockReset().mockResolvedValue({})
    test.mockReset().mockResolvedValue({ ok: true, step: 'done', message: 'Tenant, Client ID and Client Secret are valid.', redirect_uri: 'https://irdoc.example.com/api/v1/auth/oidc/callback' })
    config = {
      id: 'c1', org_id: 'o1', is_enabled: false, tenant_id: TENANT, client_id: CLIENT,
      role_mappings: {}, graph_group_lookup: false, redirect_uri: 'https://irdoc.example.com/api/v1/auth/oidc/callback',
    }
  })

  it('needs the secret again before saving a new mapping', () => {
    renderSection()
    expect(saveBtn()).toBeDisabled() // nothing changed yet

    fireEvent.click(screen.getByRole('button', { name: '+ Add Mapping' }))
    fireEvent.change(screen.getByPlaceholderText('Group / user Object ID (GUID) or app role'), { target: { value: 'g1' } })
    expect(saveBtn()).toBeDisabled()
    expect(screen.getByText(/Enter the client secret again to save changes/)).toBeInTheDocument()

    fireEvent.change(secret(), { target: { value: 's3cret' } })
    expect(saveBtn()).toBeEnabled()
  })

  it('cannot be enabled before a passing connection test', async () => {
    const { container } = renderSection()

    fireEvent.click(toggle(container))
    expect(toggle(container).checked).toBe(false)
    expect(addToast).toHaveBeenCalledWith(expect.stringMatching(/Test connection/), 'error')

    fireEvent.change(secret(), { target: { value: 's3cret' } })
    fireEvent.click(testBtn())
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('valid'))
    expect(test).toHaveBeenCalledWith({ tenant_id: TENANT, client_id: CLIENT, client_secret: 's3cret' })

    fireEvent.click(toggle(container))
    expect(toggle(container).checked).toBe(true)
  })

  it('a failed test keeps SSO off and shows why', async () => {
    test.mockResolvedValue({ ok: false, step: 'credentials', message: 'Invalid client secret. (AADSTS7000215)', redirect_uri: '' })
    const { container } = renderSection()

    fireEvent.change(secret(), { target: { value: 'wrong' } })
    fireEvent.click(testBtn())
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('AADSTS7000215'))

    fireEvent.click(toggle(container))
    expect(toggle(container).checked).toBe(false)
  })

  it('editing the client ID after a passing test locks the toggle again', async () => {
    const { container } = renderSection()
    fireEvent.change(secret(), { target: { value: 's3cret' } })
    fireEvent.click(testBtn())
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('valid'))

    fireEvent.change(screen.getAllByPlaceholderText('xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx')[1], { target: { value: 'other-client' } })
    expect(screen.getByRole('status')).toHaveTextContent('test again')

    fireEvent.click(toggle(container))
    expect(toggle(container).checked).toBe(false)
  })

  it('sends the secret and the Graph lookup flag on save', async () => {
    renderSection()
    fireEvent.click(screen.getByRole('checkbox', { name: /Look up group membership via Microsoft Graph/ }))
    fireEvent.change(secret(), { target: { value: 's3cret' } })
    fireEvent.click(saveBtn())

    await waitFor(() => expect(save).toHaveBeenCalled())
    expect(save.mock.calls[0][0]).toMatchObject({ client_secret: 's3cret', graph_group_lookup: true, is_enabled: false })
  })
})
