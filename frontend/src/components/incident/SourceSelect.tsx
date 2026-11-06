import type { IncidentSource } from '@/types/incident'
import { INCIDENT_SOURCES, INCIDENT_SOURCE_LABELS } from '@/types/incident'

interface SourceSelectProps {
  id?: string
  value: IncidentSource | ''
  onChange: (value: IncidentSource) => void
  required?: boolean
  disabled?: boolean
  /** Placeholder shown while nothing is chosen. */
  placeholder?: string
  'aria-label'?: string
}

// Dropdown of investigation triggers (#147), shared by the New Incident form,
// the close modal and the workspace header.
export function SourceSelect({
  id,
  value,
  onChange,
  required,
  disabled,
  placeholder = 'Select source…',
  'aria-label': ariaLabel,
}: SourceSelectProps) {
  return (
    <div className="select-wrap">
      <select
        id={id}
        className="form-input"
        value={value}
        onChange={(e) => onChange(e.target.value as IncidentSource)}
        required={required}
        disabled={disabled}
        aria-label={ariaLabel}
        style={{ fontFamily: 'Syne, sans-serif' }}
      >
        <option value="" disabled>{placeholder}</option>
        {INCIDENT_SOURCES.map((s) => (
          <option key={s} value={s}>{INCIDENT_SOURCE_LABELS[s]}</option>
        ))}
      </select>
    </div>
  )
}
