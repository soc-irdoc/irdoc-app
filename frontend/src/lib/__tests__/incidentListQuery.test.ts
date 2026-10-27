import { describe, expect, it } from 'vitest'
import { DEFAULT_QUERY, parseListQuery, toApiParams, toSearchParams } from '@/lib/incidentListQuery'
import { pageWindow } from '@/lib/pagination'

// #127 / #128: the list view is kept in the URL.
describe('incident list query', () => {
  it('defaults to page 1 of 25, newest first', () => {
    expect(parseListQuery(new URLSearchParams())).toEqual(DEFAULT_QUERY)
    expect(toSearchParams(DEFAULT_QUERY).toString()).toBe('')
  })

  it('round-trips through the URL', () => {
    const q = { page: 3, perPage: 50, status: 'contained' as const, search: 'phish', sort: 'severity' as const, order: 'desc' as const }
    expect(parseListQuery(toSearchParams(q))).toEqual(q)
  })

  it('ignores invalid values', () => {
    const q = parseListQuery(new URLSearchParams('page=-2&per_page=7&status=archived&sort=bogus&order=up'))
    expect(q).toEqual(DEFAULT_QUERY)
  })

  it('uses the natural first direction when only a sort is given', () => {
    expect(parseListQuery(new URLSearchParams('sort=severity')).order).toBe('desc')
    expect(parseListQuery(new URLSearchParams('sort=title')).order).toBe('asc')
  })

  it('maps to API params', () => {
    expect(toApiParams({ ...DEFAULT_QUERY, status: 'open', search: 'x' })).toEqual({
      status: 'open', search: 'x', page: 1, per_page: 25, sort: 'created', order: 'desc',
    })
    expect(toApiParams(DEFAULT_QUERY).status).toBeUndefined()
  })
})

describe('pageWindow', () => {
  it('shows every page when there are few', () => {
    expect(pageWindow(1, 3)).toEqual([1, 2, 3])
  })

  it('collapses the middle with gaps', () => {
    expect(pageWindow(6, 12)).toEqual([1, 'gap', 5, 6, 7, 'gap', 12])
    expect(pageWindow(1, 12)).toEqual([1, 2, 3, 4, 'gap', 12])
    expect(pageWindow(12, 12)).toEqual([1, 'gap', 9, 10, 11, 12])
  })
})
