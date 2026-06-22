import { useEffect, useRef, useState } from 'react'
import { useIncident, useUpdateIncident } from '@/hooks/useIncident'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { RichTextEditor } from '@/components/common/RichTextEditor'
import { useUIStore } from '@/stores/uiStore'
import { SEVERITY_LABELS, STATUS_LABELS, type UpdateIncidentPayload } from '@/types/incident'
import { formatDateTime, formatRelative } from '@/lib/utils'

interface SummaryPageProps {
  incidentId: string
}

// ── Stat card ────────────────────────────────────────────────
function StatCard({ title, value, color }: { title: string; value: string | number; color?: string }) {
  return (
    <div
      style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderTop: `2px solid ${color ?? 'var(--border)'}`,
        borderRadius: 16,
        padding: 18,
      }}
    >
      <h3
        style={{
          fontSize: 12,
          color: 'var(--text-muted)',
          textTransform: 'uppercase',
          letterSpacing: '0.5px',
          marginBottom: 8,
        }}
      >
        {title}
      </h3>
      <p
        style={{
          fontSize: 28,
          fontWeight: 800,
          color: color ?? 'var(--text-primary)',
          fontVariantNumeric: 'tabular-nums',
          letterSpacing: '-0.02em',
          wordBreak: 'break-word',
          overflowWrap: 'anywhere',
          lineHeight: 1.2,
        }}
      >
        {value}
      </p>
    </div>
  )
}

// ── Save state indicator ──────────────────────────────────────
type SaveState = 'idle' | 'dirty' | 'saving' | 'saved' | 'error'

function SaveIndicator({ state }: { state: SaveState }) {
  if (state === 'idle') return null

  if (state === 'dirty' || state === 'saving') {
    const label = state === 'saving' ? 'Saving…' : 'Unsaved changes'
    return (
      <span style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, color: 'var(--yellow)' }}>
        <span
          style={{
            width: 6,
            height: 6,
            borderRadius: '50%',
            background: 'var(--yellow)',
            display: 'inline-block',
          }}
        />
        {label}
      </span>
    )
  }

  if (state === 'saved') {
    return (
      <span style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, color: 'var(--green)' }}>
        <span
          style={{
            width: 6,
            height: 6,
            borderRadius: '50%',
            background: 'var(--green)',
            display: 'inline-block',
          }}
        />
        Saved
      </span>
    )
  }

  if (state === 'error') {
    return (
      <span style={{ fontSize: 11, color: 'var(--red)' }}>
        Save failed
      </span>
    )
  }

  return null
}

// ── Rich text section card ────────────────────────────────────
type RichTextFieldKey = keyof Pick<
  UpdateIncidentPayload,
  'executive_summary' | 'notes' | 'lessons_learned' | 'actions_todo'
>

interface RichTextSectionProps {
  title: React.ReactNode
  fieldKey: RichTextFieldKey
  content: string
  incidentId: string
  placeholder?: string
  enableTaskList?: boolean
}

function RichTextSection({
  title,
  fieldKey,
  content,
  incidentId,
  placeholder,
  enableTaskList,
}: RichTextSectionProps) {
  const addToast = useUIStore((s) => s.addToast)
  const updateIncident = useUpdateIncident(incidentId)
  const [saveState, setSaveState] = useState<SaveState>('idle')
  const timerRef = useRef<ReturnType<typeof setTimeout>>()
  const savedTimerRef = useRef<ReturnType<typeof setTimeout>>()
  // Incremented on every keystroke. The in-flight save only transitions to
  // 'saved' when the generation it was started with is still current, preventing
  // a slow save from clearing isDirty after the user has typed more.
  const saveGenRef = useRef(0)

  useEffect(() => {
    return () => {
      clearTimeout(timerRef.current)
      clearTimeout(savedTimerRef.current)
    }
  }, [])

  const isDirty = saveState === 'dirty' || saveState === 'saving'

  function handleChange(html: string) {
    setSaveState('dirty')
    clearTimeout(timerRef.current)
    const gen = ++saveGenRef.current
    timerRef.current = setTimeout(async () => {
      setSaveState('saving')
      try {
        await updateIncident.mutateAsync({ [fieldKey]: html })
        if (saveGenRef.current === gen) {
          setSaveState('saved')
          savedTimerRef.current = setTimeout(() => setSaveState('idle'), 3000)
        }
      } catch {
        addToast('Failed to save changes', 'error')
        if (saveGenRef.current === gen) setSaveState('error')
      }
    }, 2500)
  }

  return (
    <div
      style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderRadius: 12,
        marginBottom: 16,
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 16px',
          borderBottom: '1px solid var(--border)',
        }}
      >
        <h3 style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>{title}</h3>
        <SaveIndicator state={saveState} />
      </div>
      <RichTextEditor
        content={content}
        onChange={handleChange}
        placeholder={placeholder}
        enableTaskList={enableTaskList}
        isDirty={isDirty}
      />
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────
export function SummaryPage({ incidentId }: SummaryPageProps) {
  const { data: incident, isLoading } = useIncident(incidentId)

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <LoadingSpinner />
      </div>
    )
  }
  if (!incident) return null

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: 24 }}>
      <h2
        style={{
          fontSize: 18,
          fontWeight: 800,
          marginBottom: 20,
          color: 'var(--text-primary)',
          display: 'flex',
          alignItems: 'center',
          gap: 10,
        }}
      >
        <img src="/icons/bar_chart_color.svg" width={24} height={24} alt="" aria-hidden="true" /> Incident Summary
      </h2>

      {/* Severity + Status */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
          gap: 16,
          marginBottom: 20,
        }}
      >
        <StatCard title="Severity" value={SEVERITY_LABELS[incident.severity]} color="var(--red)" />
        <StatCard title="Status" value={STATUS_LABELS[incident.status]} color="var(--accent)" />
      </div>

      {/* Incident details */}
      <div
        style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border)',
          borderRadius: 12,
          padding: 20,
          marginBottom: 16,
        }}
      >
        <h3
          style={{
            fontSize: 13,
            fontWeight: 700,
            marginBottom: 12,
            color: 'var(--text-primary)',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}
        >
          <img src="/icons/clipboard_color.svg" width={20} height={20} alt="" aria-hidden="true" /> Incident Details
        </h3>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <tbody>
            {[
              ['Reference', incident.incident_ref],
              ['Created', formatDateTime(incident.created_at)],
              ['Last Updated', formatRelative(incident.updated_at)],
              ...(incident.contained_at ? [['Contained', formatDateTime(incident.contained_at)]] : []),
              ...(incident.closed_at ? [['Closed', formatDateTime(incident.closed_at)]] : []),
              ...(incident.attack_vector.length > 0
                ? [['Attack Vector', incident.attack_vector.join(', ')]]
                : []),
            ].map(([label, value]) => (
              <tr key={label}>
                <td
                  style={{
                    padding: '8px 12px 8px 0',
                    color: 'var(--text-muted)',
                    fontWeight: 600,
                    width: 160,
                    verticalAlign: 'top',
                  }}
                >
                  {label}
                </td>
                <td
                  style={{
                    padding: '8px 0',
                    color: 'var(--text-primary)',
                    fontFamily: 'JetBrains Mono, monospace',
                  }}
                >
                  {value}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Executive Summary */}
      <RichTextSection
        title={<><img src="/icons/memo_color.svg" width={20} height={20} alt="" aria-hidden="true" style={{ verticalAlign: 'middle', marginRight: 6 }} />Executive Summary</>}
        fieldKey="executive_summary"
        content={incident.executive_summary ?? ''}
        incidentId={incidentId}
        placeholder="Write an executive summary of this incident…"
      />

      {/* Notes */}
      <RichTextSection
        title={<><img src="/icons/spiral_notepad_color.svg" width={20} height={20} alt="" aria-hidden="true" style={{ verticalAlign: 'middle', marginRight: 6 }} />Notes</>}
        fieldKey="notes"
        content={incident.notes ?? ''}
        incidentId={incidentId}
        placeholder="Investigation notes, observations, key findings…"
      />

      {/* Lessons Learned */}
      <RichTextSection
        title={<><img src="/icons/light_bulb_color.svg" width={20} height={20} alt="" aria-hidden="true" style={{ verticalAlign: 'middle', marginRight: 6 }} />Lessons Learned</>}
        fieldKey="lessons_learned"
        content={incident.lessons_learned ?? ''}
        incidentId={incidentId}
        placeholder="What worked, what didn't, and what to improve for next time…"
      />

      {/* Actions To Do */}
      <RichTextSection
        title={<><img src="/icons/check_mark_button_color.svg" width={20} height={20} alt="" aria-hidden="true" style={{ verticalAlign: 'middle', marginRight: 6 }} />Actions To Do</>}
        fieldKey="actions_todo"
        content={incident.actions_todo ?? ''}
        incidentId={incidentId}
        placeholder="Click ☑ Task to add a follow-up action item…"
        enableTaskList
      />
    </div>
  )
}
