// Effort recorded on timeline entries, in minutes (#165)
export const MAX_TIME_SPENT = 1440

export function formatMinutes(minutes: number): string {
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  if (h && m) return `${h} h ${m} min`
  if (h) return `${h} h`
  return `${m} min`
}
