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

export function ExternalRefBadge({ externalRef: ref }: ExternalRefBadgeProps) {
  const label = SOURCE_LABELS[ref.external_source] ?? ref.external_source

  if (ref.external_url) {
    return (
      <a
        href={ref.external_url}
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
