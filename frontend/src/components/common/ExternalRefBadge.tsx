import type { IncidentExternalRef } from '@/types/incident'
import { FaArrowUpRightFromSquare } from 'react-icons/fa6'

const SOURCE_LABELS: Record<string, string> = {
  servicedesk_plus: 'SDP',
  manage_engine:    'ME',
  jira:             'Jira',
  servicenow:       'SN',
}

interface ExternalRefBadgeProps {
  // Not `ref`: React 18 reserves it and never passes it to a function
  // component, which crashed every page showing an external ref (#145).
  externalRef: IncidentExternalRef
}

// The URL comes from whoever called the webhook: link only to http(s), never
// javascript:/data: (the backend also rejects those; this covers stored rows).
function safeHttpUrl(url: string | null | undefined): string | null {
  if (!url) return null
  try {
    const u = new URL(url)
    return u.protocol === 'http:' || u.protocol === 'https:' ? u.href : null
  } catch {
    return null
  }
}

export function ExternalRefBadge({ externalRef: ref }: ExternalRefBadgeProps) {
  const label = SOURCE_LABELS[ref.external_source] ?? ref.external_source
  const href = safeHttpUrl(ref.external_url)

  if (href) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="chip chip-blue"
        title={`Open in ${ref.external_source}`}
      >
        {`${label}-${ref.external_ref}`}
        <FaArrowUpRightFromSquare size={9} aria-hidden="true" />
      </a>
    )
  }

  return (
    <span className="chip chip-blue" title={ref.external_source}>
      {`${label}-${ref.external_ref}`}
    </span>
  )
}
