interface ToggleSwitchProps {
  checked: boolean
  onChange: (checked: boolean) => void
  disabled?: boolean
  ariaLabel?: string
}

export function ToggleSwitch({ checked, onChange, disabled, ariaLabel }: ToggleSwitchProps) {
  return (
    <label
      className="toggle-switch"
      style={{
        position: 'relative',
        width: 40,
        height: 22,
        cursor: disabled ? 'not-allowed' : 'pointer',
        flexShrink: 0,
        display: 'inline-block',
      }}
      aria-label={ariaLabel}
    >
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => !disabled && onChange(e.target.checked)}
        style={{ display: 'none' }}
      />
      <span
        style={{
          position: 'absolute',
          inset: 0,
          borderRadius: 11,
          border: `1px solid ${checked ? 'var(--green)' : 'var(--border)'}`,
          background: checked ? 'var(--green-dim)' : 'var(--bg-elevated)',
          transition: '0.2s',
        }}
      >
        <span
          style={{
            position: 'absolute',
            width: 16,
            height: 16,
            borderRadius: '50%',
            top: 2,
            left: 2,
            background: checked ? 'var(--green)' : 'var(--text-muted)',
            transition: '0.2s',
            transform: checked ? 'translateX(18px)' : 'none',
          }}
        />
      </span>
    </label>
  )
}
