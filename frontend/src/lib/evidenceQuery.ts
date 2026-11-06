// The Evidence register view (#150) lives in the URL so a filtered view can
// be shared. Defaults are left out to keep links short.

import type { EvidenceKind } from '@/types/evidence'

export type EvidenceSortKey =
  | 'name' | 'kind' | 'source' | 'type' | 'size' | 'sha256' | 'uploaded_by' | 'uploaded_at' | 'screenshot'
export type EvidenceView = 'files' | 'iocs'
export type EvidenceTypeFilter = 'all' | 'image/' | 'application/pdf' | 'text/' | 'application/json' | 'application/'

export interface EvidenceQuery {
  view: EvidenceView
  page: number
  perPage: number
  kind: EvidenceKind | 'all'
  type: EvidenceTypeFilter
  search: string
  hideScreenshots: boolean
  sort: EvidenceSortKey
  order: 'asc' | 'desc'
}

export const EVIDENCE_PAGE_SIZES = [25, 50, 100] as const

export const DEFAULT_EVIDENCE_QUERY: EvidenceQuery = {
  view: 'files',
  page: 1,
  perPage: 50,
  kind: 'all',
  type: 'all',
  search: '',
  hideScreenshots: false,
  sort: 'uploaded_at',
  order: 'desc',
}

export const EVIDENCE_TYPE_FILTERS: Array<{ value: EvidenceTypeFilter; label: string }> = [
  { value: 'all', label: 'All types' },
  { value: 'image/', label: 'Images' },
  { value: 'application/pdf', label: 'PDF' },
  { value: 'text/', label: 'Text / CSV' },
  { value: 'application/json', label: 'JSON' },
  { value: 'application/', label: 'Other documents & binaries' },
]

const SORT_KEYS: EvidenceSortKey[] = [
  'name', 'kind', 'source', 'type', 'size', 'sha256', 'uploaded_by', 'uploaded_at', 'screenshot',
]

export function parseEvidenceQuery(params: URLSearchParams): EvidenceQuery {
  const d = DEFAULT_EVIDENCE_QUERY
  const page = Number.parseInt(params.get('page') ?? '', 10)
  const perPage = Number.parseInt(params.get('per_page') ?? '', 10)
  const sort = params.get('sort') as EvidenceSortKey | null
  const order = params.get('order')
  const kind = params.get('kind')
  const type = params.get('type') as EvidenceTypeFilter | null
  return {
    view: params.get('view') === 'iocs' ? 'iocs' : 'files',
    page: page >= 1 ? page : d.page,
    perPage: (EVIDENCE_PAGE_SIZES as readonly number[]).includes(perPage) ? perPage : d.perPage,
    kind: kind === 'timeline' || kind === 'incident' ? kind : 'all',
    type: type && EVIDENCE_TYPE_FILTERS.some((t) => t.value === type) ? type : 'all',
    search: params.get('q') ?? '',
    hideScreenshots: params.get('hide_screenshots') === '1',
    sort: sort && SORT_KEYS.includes(sort) ? sort : d.sort,
    order: order === 'asc' || order === 'desc' ? order : d.order,
  }
}

export function toEvidenceSearchParams(q: EvidenceQuery): URLSearchParams {
  const d = DEFAULT_EVIDENCE_QUERY
  const p = new URLSearchParams()
  if (q.view !== d.view) p.set('view', q.view)
  if (q.kind !== 'all') p.set('kind', q.kind)
  if (q.type !== 'all') p.set('type', q.type)
  if (q.search) p.set('q', q.search)
  if (q.hideScreenshots) p.set('hide_screenshots', '1')
  if (q.sort !== d.sort || q.order !== d.order) {
    p.set('sort', q.sort)
    p.set('order', q.order)
  }
  if (q.perPage !== d.perPage) p.set('per_page', String(q.perPage))
  if (q.page !== 1) p.set('page', String(q.page))
  return p
}

/** Filter + sort params shared by the list and the CSV export. */
export function toEvidenceApiParams(q: EvidenceQuery) {
  return {
    kind: q.kind !== 'all' ? q.kind : undefined,
    mime: q.type !== 'all' ? q.type : undefined,
    q: q.search || undefined,
    hide_screenshots: q.hideScreenshots || undefined,
    sort: q.sort,
    order: q.order,
  }
}
