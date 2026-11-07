import { useEffect, useState } from 'react'
import { Modal } from '@/components/common/Modal'
import { Button } from '@/components/common/Button'
import type { Disposition, IncidentSource } from '@/types/incident'
import { DISPOSITIONS, DISPOSITION_LABELS } from '@/types/incident'
import { SourceSelect } from '@/components/incident/SourceSelect'

export interface CloseIncidentChoice {
  disposition?: Disposition
  source?: IncidentSource
}

interface CloseIncidentModalProps {
  open: boolean
  incidentRef: string
  /** Ask for the final disposition (#124). */
  needDisposition?: boolean
  /** Ask for the investigation trigger, for incidents created before it was required (#147). */
  needSource?: boolean
  loading?: boolean
  onConfirm: (choice: CloseIncidentChoice) => void
  onClose: () => void
}

// Asked when an incident is closed without a disposition and/or a source.
// The API refuses to close an incident that is missing either.
export function CloseIncidentModal({
  open,
  incidentRef,
  needDisposition = true,
  needSource = false,
  loading,
  onConfirm,
  onClose,
}: CloseIncidentModalProps) {
  const [disposition, setDisposition] = useState<Disposition | null>(null)
  const [source, setSource] = useState<IncidentSource | ''>('')

  useEffect(() => {
    if (open) {
      setDisposition(null)
      setSource('')
    }
  }, [open])

  const complete = (!needDisposition || disposition !== null) && (!needSource || source !== '')

  return (
    <Modal open={open} title={`Close ${incidentRef}`} onClose={onClose}>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          if (!complete) return
          onConfirm({
            ...(needDisposition && disposition ? { disposition } : {}),
            ...(needSource && source ? { source } : {}),
          })
        }}
        style={{ display: 'flex', flexDirection: 'column', gap: 16 }}
      >
        {needSource && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <label
              htmlFor="close-incident-source"
              style={{ fontSize: 14, color: 'var(--text-secondary)' }}
            >
              This incident has no source recorded. What triggered the investigation?
            </label>
            <SourceSelect id="close-incident-source" value={source} onChange={setSource} required />
          </div>
        )}
        {needDisposition && (
          <fieldset style={{ border: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 8 }}>
            <legend style={{ fontSize: 14, color: 'var(--text-secondary)', marginBottom: 8 }}>
              Choose the final disposition of this investigation.
            </legend>
            {DISPOSITIONS.map((d) => (
              <label
                key={d}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: '8px 12px',
                  borderRadius: 8,
                  border: `1px solid ${disposition === d ? 'var(--accent)' : 'var(--border)'}`,
                  background: disposition === d ? 'var(--accent-dim)' : 'transparent',
                  cursor: 'pointer',
                  fontSize: 13,
                  color: 'var(--text-primary)',
                }}
              >
                <input
                  type="radio"
                  name="disposition"
                  value={d}
                  checked={disposition === d}
                  onChange={() => setDisposition(d)}
                  style={{ accentColor: 'var(--accent)' }}
                />
                {DISPOSITION_LABELS[d]}
              </label>
            ))}
          </fieldset>
        )}
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="accent" disabled={!complete || loading} loading={loading}>
            Close incident
          </Button>
        </div>
      </form>
    </Modal>
  )
}
