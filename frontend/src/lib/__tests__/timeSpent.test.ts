import { describe, expect, it } from 'vitest'
import { formatMinutes } from '@/lib/timeSpent'

describe('formatMinutes (#165)', () => {
  it('formats minutes and hours like the report does', () => {
    expect(formatMinutes(0)).toBe('0 min')
    expect(formatMinutes(45)).toBe('45 min')
    expect(formatMinutes(60)).toBe('1 h')
    expect(formatMinutes(135)).toBe('2 h 15 min')
  })
})
