export type TimeRangeOption = '24h' | '7d' | '30d' | '90d' | 'all'

export const TIME_RANGE_LABELS: Record<TimeRangeOption, string> = {
  '24h': 'Last 24 hours',
  '7d': 'Last 7 days',
  '30d': 'Last 30 days',
  '90d': 'Last 90 days',
  'all': 'All time',
}

export function getTimeRange(option: TimeRangeOption): { from_dt: string; to_dt: string } {
  const now = new Date()
  const to_dt = now.toISOString()

  if (option === 'all') {
    return { from_dt: '2000-01-01T00:00:00.000Z', to_dt }
  }

  const ms: Record<TimeRangeOption, number> = {
    '24h': 24 * 60 * 60 * 1000,
    '7d': 7 * 24 * 60 * 60 * 1000,
    '30d': 30 * 24 * 60 * 60 * 1000,
    '90d': 90 * 24 * 60 * 60 * 1000,
    'all': 0,
  }

  const from = new Date(now.getTime() - ms[option])
  return { from_dt: from.toISOString(), to_dt }
}
