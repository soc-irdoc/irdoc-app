import { describe, expect, it } from 'vitest'
import { AxiosError, AxiosHeaders } from 'axios'
import { getLoginErrorMessage } from '@/lib/utils'

function httpError(status: number, data: unknown) {
  const config = { headers: new AxiosHeaders() }
  return new AxiosError('fail', 'ERR', config, null, {
    status, statusText: '', headers: {}, config, data,
  })
}

describe('getLoginErrorMessage', () => {
  it('shows the backend detail for rejected credentials', () => {
    expect(getLoginErrorMessage(httpError(401, { detail: 'Invalid email or password' })))
      .toBe('Invalid email or password')
  })

  it('does not blame the password when the backend is down or restarting', () => {
    expect(getLoginErrorMessage(httpError(502, '<html>Bad Gateway</html>'))).toMatch(/Cannot reach/)
    expect(getLoginErrorMessage(new AxiosError('Network Error', 'ERR_NETWORK'))).toMatch(/Cannot reach/)
  })

  it('explains the login rate limit', () => {
    expect(getLoginErrorMessage(httpError(429, { error: 'Rate limit exceeded' }))).toMatch(/Too many/)
  })

  it('handles validation errors whose detail is a list', () => {
    expect(getLoginErrorMessage(httpError(422, { detail: [{ msg: 'bad email' }] })))
      .toBe('Enter a valid email address and password.')
  })
})
