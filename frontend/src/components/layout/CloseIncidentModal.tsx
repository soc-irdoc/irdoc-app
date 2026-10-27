import { useEffect, useState } from 'react'
import { Modal } from '@/components/common/Modal'
import { Button } from '@/components/common/Button'
import type { Disposition } from '@/types/incident'
import { DISPOSITIONS, DISPOSITION_LABELS } from '@/types/incident'

interface CloseIncidentModalProps {
  open: boolean
  incidentRef: string
  loading?: boolean
  onConfirm: (disposition: Disposition) => void
  onClose: () => void
}

// Asked when an incident is closed: how did the investigation end? (#124)
// The API refuses to close an incident without a disposition.
export function CloseIncidentModal({ open, incidentRef, loading, onConfirm, onClose }: CloseIncidentModalProps) {
  const [choice, setChoice] = useState<Disposition | null>(null)

  useEffect(() => {
    if (open) setChoice(null)
  }, [open])

  return (
    <Modal open={open} title={`Close ${incidentRef}`} onClose={onClose}>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          if (choice) onConfirm(choice)
        }}
        style={{ display: 'flex', flexDirection: 'column', gap: 16 }}
      >
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
                border: `1px solid ${choice === d ? 'var(--accent)' : 'var(--border)'}`,
                background: choice === d ? 'var(--accent-dim)' : 'transparent',
                cursor: 'pointer',
                fontSize: 13,
                color: 'var(--text-primary)',
              }}
            >
              <input
                type="radio"
                name="disposition"
                value={d}
                checked={choice === d}
                onChange={() => setChoice(d)}
                style={{ accentColor: 'var(--accent)' }}
              />
              {DISPOSITION_LABELS[d]}
            </label>
          ))}
        </fieldset>
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="accent" disabled={!choice || loading} loading={loading}>
            Close incident
          </Button>
        </div>
      </form>
    </Modal>
  )
}
