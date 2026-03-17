import type { EntryType } from '@/types/timeline'

const FILTER_OPTIONS: Array<{ value: EntryType | 'all'; label: string }> = [
  { value: 'all',         label: 'All' },
  { value: 'detection',   label: 'Detection' },
  { value: 'analysis',    label: 'Analysis' },
  { value: 'containment', label: 'Containment' },
  { value: 'evidence',    label: 'Evidence' },
  { value: 'comms',       label: 'Comms' },
  { value: 'note',        label: 'Note' },
]

interface TimelineFiltersProps {
  active: EntryType | 'all'
  onChange: (filter: EntryType | 'all') => void
  onExportCSV: () => void
}

export function TimelineFilters({ active, onChange, onExportCSV }: TimelineFiltersProps) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        marginBottom: 20,
        flexWrap: 'wrap',
      }}
    >
      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', flex: 1 }}>
        {FILTER_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => onChange(opt.value)}
            className={`btn btn-sm ${active === opt.value ? 'btn-accent' : 'btn-ghost'}`}
          >
            {opt.label}
          </button>
        ))}
      </div>
      <button
        className="btn btn-ghost btn-sm"
        onClick={onExportCSV}
        title="Export timeline as CSV"
      >
        ↓ Export CSV
      </button>
    </div>
  )
}
