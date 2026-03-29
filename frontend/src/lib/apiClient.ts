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

// Inject access token on every request
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) {
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
      // Avoid refresh loop on auth endpoints
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

export default apiClient
