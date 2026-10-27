/** Page numbers to show: always the first and last, plus a window around the current page. */
export function pageWindow(page: number, lastPage: number): Array<number | 'gap'> {
  const pages = new Set([1, lastPage, page - 1, page, page + 1])
  if (page <= 3) [2, 3, 4].forEach((p) => pages.add(p))
  if (page >= lastPage - 2) [lastPage - 1, lastPage - 2, lastPage - 3].forEach((p) => pages.add(p))
  const sorted = [...pages].filter((p) => p >= 1 && p <= lastPage).sort((a, b) => a - b)
  const out: Array<number | 'gap'> = []
  sorted.forEach((p, i) => {
    if (i > 0 && p - sorted[i - 1] > 1) out.push('gap')
    out.push(p)
  })
  return out
}
