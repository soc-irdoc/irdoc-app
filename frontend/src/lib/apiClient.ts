import axios from 'axios'
import { useAuthStore } from '@/stores/authStore'
import { applySessionMeta, hasActivitySince } from '@/lib/activity'

const apiClient = axios.create({
  baseURL: '/api/v1',
  withCredentials: true, // needed for refresh token cookie
})

// Decode the JWT exp field (seconds since epoch) without a library
function getTokenExpiry(token: string): number | null {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return typeof payload.exp === 'number' ? payload.exp * 1000 : null
  } catch {
    return null
  }
}

let proactiveRefreshTimer: ReturnType<typeof setTimeout> | null = null
// When the current access token was received. A refresh is only made for a
// user who did something since then, so an idle session isn't kept alive
// by timers or background requests (#123).
let tokenReceivedAt = Date.now()

export function cancelTokenTimers() {
  if (proactiveRefreshTimer) { clearTimeout(proactiveRefreshTimer); proactiveRefreshTimer = null }
}

/** POST /auth/refresh with the cookie; applies the new token and session limits. */
export async function refreshSession() {
  // Plain axios, not apiClient: a 401 here must not re-enter the interceptor.
  const res = await axios.post('/api/v1/auth/refresh', {}, { withCredentials: true })
  const token: string = res.data.data.access_token
  applySessionMeta(res.data.meta?.session)
  useAuthStore.getState().setToken(token)
  scheduleTokenRefresh(token)
  return { token, user: res.data.user }
}

// Silently refresh 1 min before the access token expires, if the user was
// active since it was issued. Called every time we receive a new access token.
export function scheduleTokenRefresh(token: string) {
  if (proactiveRefreshTimer) clearTimeout(proactiveRefreshTimer)
  tokenReceivedAt = Date.now()

  const expiresAt = getTokenExpiry(token)
  if (!expiresAt) return

  const refreshAt = expiresAt - 1 * 60 * 1000
  const delay = refreshAt - Date.now()
  if (delay <= 0) return

  proactiveRefreshTimer = setTimeout(async () => {
    proactiveRefreshTimer = null
    // Idle since the last token: let it expire. The next request after the
    // user comes back refreshes it (if the session is still alive).
    if (!hasActivitySince(tokenReceivedAt)) return
    try {
      await refreshSession()
    } catch {
      // Refresh failed silently - the next API call will handle the 401
    }
  }, delay)
}

// Inject access token on every request, but never override an explicitly-set
// Authorization header (e.g. mfa_challenge or mfa_setup tokens passed directly).
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let isRefreshing = false
let refreshQueue: Array<{ resolve: (token: string) => void; reject: (err: unknown) => void }> = []

function processQueue(token: string) {
  refreshQueue.forEach(({ resolve }) => resolve(token))
  refreshQueue = []
}

function rejectQueue(err: unknown) {
  refreshQueue.forEach(({ reject }) => reject(err))
  refreshQueue = []
}

// 401 interceptor - attempt token refresh, then retry
apiClient.interceptors.response.use(
  (response) => {
    // Login, MFA, invite acceptance... carry the session limits (#123).
    applySessionMeta(response.data?.meta?.session)
    return response
  },
  async (error) => {
    const original = error.config

    if (error.response?.status === 401 && !original._retry) {
      // MFA action endpoints: 401 means wrong code, not an expired session.
      // Let the calling component handle the error directly - no redirect or reload.
      const mfaActionUrls = ['/auth/mfa/verify', '/auth/mfa/setup/complete']
      if (mfaActionUrls.some((u) => original.url?.includes(u))) {
        return Promise.reject(error)
      }

      // Avoid refresh loop on other auth endpoints
      if (original.url?.includes('/auth/')) {
        useAuthStore.getState().clearAuth()
        window.location.href = '/login'
        return Promise.reject(error)
      }

      // A background request (polling, refetch) while the user is away must
      // not keep the session alive: fail it, and leave signing out to the
      // idle timer (#123).
      if (!hasActivitySince(tokenReceivedAt)) {
        return Promise.reject(error)
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          refreshQueue.push({
            resolve: (token) => {
              original.headers.Authorization = `Bearer ${token}`
              resolve(apiClient(original))
            },
            reject,
          })
        })
      }

      original._retry = true
      isRefreshing = true

      try {
        const { token: newToken } = await refreshSession()
        processQueue(newToken)
        original.headers.Authorization = `Bearer ${newToken}`
        return apiClient(original)
      } catch (err) {
        rejectQueue(err)
        useAuthStore.getState().clearAuth()
        window.location.href = '/login?reason=session_expired'
        return Promise.reject(error)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  }
)

export const mfaApi = {
  getSetup: (token: string) =>
    apiClient.get<{ data: { secret_uri: string } }>('/auth/mfa/setup', {
      headers: { Authorization: `Bearer ${token}` },
    }),

  getSetupWithAccessToken: () =>
    apiClient.get<{ data: { secret_uri: string } }>('/auth/mfa/setup'),

  completeSetup: (token: string, code: string) =>
    apiClient.post<{ data: { access_token: string; backup_codes: string[]; user: import('@/types/user').User } }>(
      '/auth/mfa/setup/complete',
      { code },
      { headers: { Authorization: `Bearer ${token}` } },
    ),

  completeSetupWithAccessToken: (code: string) =>
    apiClient.post<{ data: { access_token: string; backup_codes: string[]; user: import('@/types/user').User } }>(
      '/auth/mfa/setup/complete',
      { code },
    ),

  verify: (token: string, code: string) =>
    apiClient.post<{ data: { access_token: string; user: import('@/types/user').User } }>(
      '/auth/mfa/verify',
      { code },
      { headers: { Authorization: `Bearer ${token}` } },
    ),

  regenerateBackupCodes: () =>
    apiClient.post<{ data: { codes: string[] } }>('/auth/mfa/backup-codes/regenerate', {}),

  disable: () =>
    apiClient.delete('/auth/mfa/disable'),
}

export const versionApi = {
  get: () =>
    apiClient.get<{
      data: { version: string; latest_version: string | null; update_available: boolean }
    }>('/version'),
}

export default apiClient
