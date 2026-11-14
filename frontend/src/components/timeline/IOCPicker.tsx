import type { IOC } from '@/types/ioc'

// Toggle chips for linking an incident's IOCs to a timeline entry (#152).
// Shared by the add form and the edit modal; looks like the asset picker.
export function IOCPicker({
  iocs,
  selectedIds,
  onToggle,
  disabled = false,
}: {
  iocs: IOC[]
  selectedIds: Set<string>
  onToggle: (iocId: string) => void
  disabled?: boolean
}) {
  return (
    <div
      role="group"
      aria-label="IOCs seen in this entry"
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: 6,
        padding: '10px 12px',
        background: 'var(--bg-base)',
        borderRadius: 8,
        border: '1px solid var(--border-subtle)',
      }}
    >
      {iocs.map((ioc) => {
        const selected = selectedIds.has(ioc.id)
        return (
          <button
            key={ioc.id}
            type="button"
            aria-pressed={selected}
            disabled={disabled}
            onClick={() => onToggle(ioc.id)}
            title={`${ioc.ioc_type}: ${ioc.value}`}
            style={{
              padding: '4px 10px',
              borderRadius: 6,
              border: `1px solid ${selected ? 'var(--accent)' : 'var(--border)'}`,
              background: selected ? 'var(--accent-dim)' : 'var(--bg-card)',
              color: selected ? 'var(--accent)' : 'var(--text-secondary)',
              cursor: disabled ? 'default' : 'pointer',
              fontSize: 12,
              display: 'flex',
              alignItems: 'center',
              gap: 5,
              maxWidth: 320,
            }}
          >
            <span style={{ fontSize: 10, opacity: 0.6, textTransform: 'uppercase' }}>{ioc.ioc_type}</span>
            <span style={{ fontFamily: 'JetBrains Mono, monospace', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {ioc.value}
            </span>
          </button>
        )
      })}
    </div>
  )
}
