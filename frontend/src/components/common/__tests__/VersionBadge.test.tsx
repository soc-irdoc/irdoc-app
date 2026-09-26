import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { VersionBadge } from '../VersionBadge'

const versionState = { version: '0.1.2-alpha' as string | undefined, latestVersion: null as string | null, updateAvailable: false }
vi.mock('@/hooks/useVersion', () => ({ useVersion: () => versionState }))

describe('VersionBadge', () => {
  beforeEach(() => {
    Object.assign(versionState, { version: '0.1.2-alpha', latestVersion: null, updateAvailable: false })
  })

  it('shows a grey badge with the running version when up to date', () => {
    render(<VersionBadge />)
    const badge = screen.getByRole('link')
    expect(badge).toHaveTextContent('v0.1.2-alpha')
    expect(badge).toHaveAttribute('data-update-available', 'false')
    expect(badge.style.color).toBe('var(--text-muted)')
  })

  it('turns yellow and names the new version when an update exists', () => {
    Object.assign(versionState, { latestVersion: '0.1.3-alpha', updateAvailable: true })
    render(<VersionBadge />)
    const badge = screen.getByRole('link')
    expect(badge).toHaveTextContent('v0.1.2-alpha → v0.1.3-alpha')
    expect(badge.style.color).toBe('var(--yellow)')
    expect(badge).toHaveAttribute('href', 'https://github.com/soc-irdoc/irdoc-app/releases/tag/v0.1.3-alpha')
  })

  it('compact form shows only the numeric version', () => {
    Object.assign(versionState, { latestVersion: '0.1.3-alpha', updateAvailable: true })
    render(<VersionBadge compact />)
    expect(screen.getByRole('link')).toHaveTextContent(/^v0\.1\.2$/)
  })

  it('renders nothing before the version is known', () => {
    versionState.version = undefined
    const { container } = render(<VersionBadge />)
    expect(container).toBeEmptyDOMElement()
  })
})
