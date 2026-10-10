import { useThemeStore } from '@/stores/themeStore'
import irdocDark from '@/assets/irdoc_dark.svg'
import irdocLight from '@/assets/irdoc_light.svg'

interface BrandLogoProps {
  size?: number
  title?: string
  onClick?: () => void
  style?: React.CSSProperties
}

/** IRDoc logo, switched to the variant that matches the active theme. */
export function BrandLogo({ size = 72, title, onClick, style }: BrandLogoProps) {
  const { theme } = useThemeStore()
  return (
    <img
      src={theme === 'dark' ? irdocDark : irdocLight}
      alt="IRDoc"
      title={title}
      onClick={onClick}
      width={size}
      height={size}
      style={{ objectFit: 'contain', flexShrink: 0, ...style }}
    />
  )
}
