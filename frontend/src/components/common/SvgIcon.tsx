interface SvgIconProps {
  name: string
  size?: number
  style?: React.CSSProperties
}

export function SvgIcon({ name, size = 16, style }: SvgIconProps) {
  return (
    <img
      src={`/icons/${name}`}
      width={size}
      height={size}
      alt=""
      aria-hidden="true"
      style={{ display: 'inline-block', verticalAlign: 'middle', flexShrink: 0, ...style }}
    />
  )
}
