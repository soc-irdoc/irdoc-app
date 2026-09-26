/**
 * Running IRDoc version, as a pill. Grey when up to date; yellow (SEV-2
 * colour) with the newer version when a release is available, linking to it.
 */
import { useVersion } from '@/hooks/useVersion'

const RELEASES_URL = 'https://github.com/soc-irdoc/irdoc-app/releases'

interface Props {
  /** Narrow form for the collapsed left nav: version number only. */
  compact?: boolean
}

export function VersionBadge({ compact = false }: Props) {
  const { version, latestVersion, updateAvailable } = useVersion()
  if (!version) return null

  const shown = compact ? `v${version.split('-')[0]}` : `v${version}`
  const text = updateAvailable && !compact ? `${shown} → v${latestVersion}` : shown
  const title = updateAvailable
    ? `IRDoc v${version}. New version available: v${latestVersion}`
    : `IRDoc v${version} (up to date)`

  const style: React.CSSProperties = {
    display: 'inline-block',
    maxWidth: '100%',
    padding: '2px 8px',
    borderRadius: 999,
    fontSize: compact ? 10 : 11,
    fontWeight: 600,
    lineHeight: 1.5,
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    textDecoration: 'none',
    border: `1px solid ${updateAvailable ? 'var(--yellow)' : 'var(--border)'}`,
    background: updateAvailable ? 'var(--yellow-dim)' : 'var(--bg-base)',
    color: updateAvailable ? 'var(--yellow)' : 'var(--text-muted)',
  }

  return (
    <a
      href={updateAvailable ? `${RELEASES_URL}/tag/v${latestVersion}` : RELEASES_URL}
      target="_blank"
      rel="noopener noreferrer"
      title={title}
      aria-label={title}
      data-update-available={updateAvailable}
      style={style}
    >
      {text}
    </a>
  )
}
