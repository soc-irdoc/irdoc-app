import { describe, expect, it } from 'vitest'
import { AxiosError, AxiosHeaders } from 'axios'
import { getErrorMessage } from '@/lib/utils'

function httpError(status: number, data: unknown) {
  const config = { headers: new AxiosHeaders() }
  return new AxiosError('fail', 'ERR', config, null, {
    status, statusText: '', headers: {}, config, data,
  })
}

describe('getErrorMessage', () => {
  it('returns a string detail as is', () => {
    expect(getErrorMessage(httpError(409, { detail: 'Slug taken' }), 'x')).toBe('Slug taken')
  })

  it('reads FastAPI validation errors (422 detail arrays)', () => {
    const err = httpError(422, {
      detail: [
        { loc: ['body', 'logo_url'], msg: 'Value error, Logo URL must be an http(s) URL', type: 'value_error' },
        { loc: ['body', 'accent_color'], msg: "String should match pattern '^#[0-9a-fA-F]{6}$'", type: 'string_pattern_mismatch' },
      ],
    })
    expect(getErrorMessage(err, 'x')).toBe(
      "logo_url: Logo URL must be an http(s) URL; accent_color: String should match pattern '^#[0-9a-fA-F]{6}$'",
    )
  })

  it('falls back when there is no usable detail', () => {
    expect(getErrorMessage(httpError(500, '<html/>'), 'Failed')).toBe('Failed')
    expect(getErrorMessage(new Error('boom'), 'Failed')).toBe('Failed')
  })
})
