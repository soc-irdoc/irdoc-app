import { FaClock } from 'react-icons/fa6'
import { MAX_TIME_SPENT } from '@/lib/timeSpent'

const QUICK_MINUTES = [5, 15, 30, 60]

// Optional effort for a timeline entry, in minutes (#165). Empty means "not
// tracked", which reports keep apart from 0. One click for the common values.
export function TimeSpentInput({
  id,
  value,
  onChange,
}: {
  id: string
  value: number | null
  onChange: (minutes: number | null) => void
}) {
  function handleInput(raw: string) {
    if (raw.trim() === '') return onChange(null)
    const n = Math.round(Number(raw))
    if (Number.isFinite(n)) onChange(Math.min(Math.max(n, 0), MAX_TIME_SPENT))
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
      <label htmlFor={id} style={{ fontSize: 12, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 4 }}>
        <FaClock size={13} aria-hidden="true" /> Time spent
      </label>
      <input
        id={id}
        type="number"
        className="form-input"
        min={0}
        max={MAX_TIME_SPENT}
        step={1}
        inputMode="numeric"
        placeholder="optional"
        value={value ?? ''}
        onChange={(e) => handleInput(e.target.value)}
        style={{ width: 90, padding: '4px 8px', fontSize: 12 }}
        aria-describedby={`${id}-unit`}
      />
      <span id={`${id}-unit`} style={{ fontSize: 12, color: 'var(--text-muted)' }}>min</span>
      {QUICK_MINUTES.map((m) => (
        <button
          key={m}
          type="button"
          onClick={() => onChange(m)}
          aria-pressed={value === m}
          style={{
            padding: '2px 8px',
            borderRadius: 6,
            fontSize: 11,
            cursor: 'pointer',
            border: `1px solid ${value === m ? 'var(--accent)' : 'var(--border)'}`,
            background: value === m ? 'var(--accent-dim)' : 'var(--bg-card)',
            color: value === m ? 'var(--accent)' : 'var(--text-secondary)',
          }}
        >
          {m < 60 ? `${m}m` : `${m / 60}h`}
        </button>
      ))}
      {value !== null && (
        <button
          type="button"
          onClick={() => onChange(null)}
          className="btn btn-ghost btn-sm"
          style={{ fontSize: 11, padding: '2px 6px' }}
        >
          Clear
        </button>
      )}
    </div>
  )
}

