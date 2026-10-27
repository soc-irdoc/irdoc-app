// The incidents list view - page, page size, status filter, search and sort -
// lives in the URL, so a refresh or a shared link opens the same view
// (#127, #128). Defaults are left out of the URL to keep it short.

import type { IncidentStatus } from '@/types/incident'

export type IncidentSortKey = 'severity' | 'ref' | 'title' | 'owner' | 'status' | 'created'
export type SortOrder = 'asc' | 'desc'

export interface IncidentListQuery {
  page: number
  perPage: number
  status: IncidentStatus | 'all'
  search: string
  sort: IncidentSortKey
  order: SortOrder
}

export const PAGE_SIZES = [25, 50, 100] as const

export const DEFAULT_QUERY: IncidentListQuery = {
  page: 1,
  perPage: 25,
  status: 'all',
  search: '',
  sort: 'created',
  order: 'desc',
}

const STATUSES: IncidentStatus[] = ['open', 'contained', 'monitoring', 'closed']
const SORT_KEYS: IncidentSortKey[] = ['severity', 'ref', 'title', 'owner', 'status', 'created']

// First click on a header: the order that puts the most useful rows on top.
// Most severe and newest first; everything else A-Z / start of the workflow.
export const FIRST_CLICK_ORDER: Record<IncidentSortKey, SortOrder> = {
  severity: 'desc',
  created: 'desc',
  ref: 'asc',
  title: 'asc',
  owner: 'asc',
  status: 'asc',
}

export function parseListQuery(params: URLSearchParams): IncidentListQuery {
  const page = Number.parseInt(params.get('page') ?? '', 10)
  const perPage = Number.parseInt(params.get('per_page') ?? '', 10)
  const status = params.get('status') as IncidentStatus | null
  const sort = params.get('sort') as IncidentSortKey | null
  const order = params.get('order')
  const validSort = sort && SORT_KEYS.includes(sort) ? sort : DEFAULT_QUERY.sort
  return {
    page: page >= 1 ? page : DEFAULT_QUERY.page,
    perPage: (PAGE_SIZES as readonly number[]).includes(perPage) ? perPage : DEFAULT_QUERY.perPage,
    status: status && STATUSES.includes(status) ? status : 'all',
    search: params.get('q') ?? '',
    sort: validSort,
    order: order === 'asc' || order === 'desc' ? order : FIRST_CLICK_ORDER[validSort],
  }
}

export function toSearchParams(q: IncidentListQuery): URLSearchParams {
  const params = new URLSearchParams()
  if (q.status !== 'all') params.set('status', q.status)
  if (q.search) params.set('q', q.search)
  if (q.sort !== DEFAULT_QUERY.sort || q.order !== DEFAULT_QUERY.order) {
    params.set('sort', q.sort)
    params.set('order', q.order)
  }
  if (q.perPage !== DEFAULT_QUERY.perPage) params.set('per_page', String(q.perPage))
  if (q.page !== 1) params.set('page', String(q.page))
  return params
}

/** The API params for a list query. */
export function toApiParams(q: IncidentListQuery) {
  return {
    status: q.status !== 'all' ? q.status : undefined,
    search: q.search || undefined,
    page: q.page,
    per_page: q.perPage,
    sort: q.sort,
    order: q.order,
  }
}

// Remember the last list view, so "back" from an incident returns to the
// same page, filter and sort instead of the first page.
const LAST_LIST_KEY = 'irdoc:incident-list-query'

export function rememberListQuery(search: string) {
  try {
    sessionStorage.setItem(LAST_LIST_KEY, search)
  } catch {
    // Storage blocked: back goes to the default view.
  }
}

export function lastListPath(): string {
  let search = ''
  try {
    search = sessionStorage.getItem(LAST_LIST_KEY) ?? ''
  } catch {
    search = ''
  }
  return search ? `/incidents?${search}` : '/incidents'
}
