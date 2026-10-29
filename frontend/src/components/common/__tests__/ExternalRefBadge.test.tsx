import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ExternalRefBadge } from '../ExternalRefBadge'
import type { IncidentExternalRef } from '@/types/incident'

// Regression: the badge took its data as a prop named `ref`, which React 18
// reserves and never passes to a function component - so it read
// `undefined.external_source` and blanked the incident list and the incident
// page for any incident created with an external ref (webhook / API key).

const extRef = {
  id: 'r1',
  external_source: 'jira',
  external_ref: 'SEC-42',
  external_url: null,
} as unknown as IncidentExternalRef

describe('ExternalRefBadge', () => {
  it('renders the source label and ref', () => {
    render(<ExternalRefBadge externalRef={extRef} />)
    expect(screen.getByText('Jira-SEC-42')).toBeInTheDocument()
  })

  it('links to the source ticket when there is a URL', () => {
    render(<ExternalRefBadge externalRef={{ ...extRef, external_url: 'https://jira.example.com/SEC-42' }} />)
    expect(screen.getByRole('link')).toHaveAttribute('href', 'https://jira.example.com/SEC-42')
  })
})
