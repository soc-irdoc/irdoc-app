import axios from 'axios'
import { useAuthStore } from '@/stores/authStore'
import { useUIStore } from '@/stores/uiStore'

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

let expiryWarningTimer: ReturnType<typeof setTimeout> | null = null
let proactiveRefreshTimer: ReturnType<typeof setTimeout> | null = null

// Schedule a warning toast 2 min before expiry and a silent proactive refresh at 1 min before.
// Called every time we receive a new access token.
export function scheduleTokenRefresh(token: string) {
  if (expiryWarningTimer) clearTimeout(expiryWarningTimer)
  if (proactiveRefreshTimer) clearTimeout(proactiveRefreshTimer)

  const expiresAt = getTokenExpiry(token)
  if (!expiresAt) return

  const now = Date.now()
  const warnAt = expiresAt - 2 * 60 * 1000   // 2 min before expiry
  const refreshAt = expiresAt - 1 * 60 * 1000 // 1 min before expiry

  if (warnAt > now) {
    expiryWarningTimer = setTimeout(() => {
      useUIStore.getState().addToast(
        'Your session expires soon. Save your work — you may be asked to log in again.',
        'info',
      )
    }, warnAt - now)
  }

  if (refreshAt > now) {
    proactiveRefreshTimer = setTimeout(async () => {
      try {
        const res = await axios.post('/api/v1/auth/refresh', {}, { withCredentials: true })
        const newToken = res.data.data.access_token
        useAuthStore.getState().setToken(newToken)
        scheduleTokenRefresh(newToken)
      } catch {
        // Refresh failed silently — the next API call will handle the 401
      }
    }, refreshAt - now)
  }
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
let refreshQueue: Array<(token: string) => void> = []

function processQueue(token: string) {
  refreshQueue.forEach((cb) => cb(token))
  refreshQueue = []
}

// 401 interceptor — attempt token refresh, then retry
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config

    if (error.response?.status === 401 && !original._retry) {
      // MFA action endpoints: 401 means wrong code, not an expired session.
      // Let the calling component handle the error directly — no redirect or reload.
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

      if (isRefreshing) {
        return new Promise((resolve) => {
          refreshQueue.push((token: string) => {
            original.headers.Authorization = `Bearer ${token}`
            resolve(apiClient(original))
          })
        })
      }

      original._retry = true
      isRefreshing = true

      try {
        const res = await axios.post('/api/v1/auth/refresh', {}, { withCredentials: true })
        const newToken = res.data.data.access_token
        useAuthStore.getState().setToken(newToken)
        scheduleTokenRefresh(newToken)
        processQueue(newToken)
        original.headers.Authorization = `Bearer ${newToken}`
        return apiClient(original)
      } catch {
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

export default apiClient
