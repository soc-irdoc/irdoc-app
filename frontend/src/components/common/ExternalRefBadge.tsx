import type { IncidentExternalRef } from '@/types/incident'

const SOURCE_LABELS: Record<string, string> = {
  servicedesk_plus: 'SDP',
  manage_engine:    'ME',
  jira:             'Jira',
  servicenow:       'SN',
}

interface ExternalRefBadgeProps {
  ref: IncidentExternalRef
}

export function ExternalRefBadge({ ref }: ExternalRefBadgeProps) {
  const label = SOURCE_LABELS[ref.external_source] ?? ref.external_source
  const content = `${label}-${ref.external_ref} ↗`

  if (ref.external_url) {
    return (
      <a
        href={ref.external_url}
        target="_blank"
        rel="noopener noreferrer"
        className="chip chip-blue"
        title={`Open in ${ref.external_source}`}
      >
        {content}
      </a>
    )
  }

  return (
    <span className="chip chip-blue" title={ref.external_source}>
      {`${label}-${ref.external_ref}`}
    </span>
  )
}
