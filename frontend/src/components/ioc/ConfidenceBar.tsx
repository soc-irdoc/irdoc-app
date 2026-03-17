interface ConfidenceBarProps {
  value: number  // 0-100
}

export function ConfidenceBar({ value }: ConfidenceBarProps) {
  const color =
    value >= 80 ? 'var(--red)' :
    value >= 50 ? 'var(--yellow)' :
                  'var(--green)'

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div
        style={{
          height: 4,
          borderRadius: 2,
          background: 'var(--bg-elevated)',
          width: 80,
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            height: '100%',
            borderRadius: 2,
            background: color,
            width: `${value}%`,
          }}
        />
      </div>
      <span
        style={{
          fontSize: 11,
          color: 'var(--text-muted)',
          fontFamily: 'JetBrains Mono, monospace',
        }}
      >
        {value}%
      </span>
    </div>
  )
}
