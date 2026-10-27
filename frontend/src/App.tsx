import { useEffect, useState, lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { cancelTokenTimers, refreshSession, scheduleTokenRefresh } from '@/lib/apiClient'
import { startActivityTracking, stopActivityTracking } from '@/lib/activity'
import { disconnectSocket } from '@/lib/websocket'
import { useThemeStore } from '@/stores/themeStore'
import { ToastContainer } from '@/components/common/Toast'
import { LoginPage } from '@/pages/LoginPage'
import { IncidentListPage } from '@/pages/IncidentListPage'
import { OverviewPage } from '@/pages/OverviewPage'
import { IncidentWorkspacePage } from '@/pages/IncidentWorkspacePage'
import { SettingsPageWrapper } from '@/pages/SettingsPageWrapper'
import { PageLoader } from '@/components/common/LoadingSpinner'
import ReportTemplateListPage from '@/pages/ReportTemplateListPage'
import ReportTemplateEditorPage from '@/pages/ReportTemplateEditorPage'

const AdminPage = lazy(() => import('@/pages/AdminPage'))
const InviteAcceptPage = lazy(() => import('@/pages/InviteAcceptPage'))

function ProtectedRoute({ children, isRestoring }: { children: React.ReactNode; isRestoring: boolean }) {
  const user = useAuthStore((s) => s.user)
  // While the session-restore request is in flight, show a loader instead of
  // immediately redirecting. Without this, ProtectedRoute fires <Navigate to="/login">
  // before the refresh cookie is validated, replacing the history entry and losing
  // the original deep-link URL (e.g. /incidents/:id/assets).
  if (isRestoring) return <PageLoader />
  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}

export function App() {
  const { setAuth } = useAuthStore()
  const signedIn = useAuthStore((s) => s.user !== null)
  const accessToken = useAuthStore((s) => s.accessToken)
  const { theme } = useThemeStore()
  const [isRestoring, setIsRestoring] = useState(true)

  // Restore session on load by hitting /auth/refresh with the refresh cookie
  useEffect(() => {
    async function tryRestore() {
      try {
        // refreshSession uses plain axios (not apiClient), so a 401 here can't
        // trigger the interceptor's full-page redirect and a reload loop.
        const { token, user } = await refreshSession()
        setAuth(user, token)
      } catch {
        // No session - user will be redirected to login by ProtectedRoute
      } finally {
        setIsRestoring(false)
      }
    }
    tryRestore()
  }, [setAuth])

  // Every new access token (login, MFA, refresh) gets its proactive refresh.
  useEffect(() => {
    if (accessToken) scheduleTokenRefresh(accessToken)
    else cancelTokenTimers()
  }, [accessToken])

  // Sign this tab out after the session's idle timeout (#123). The cookie is
  // left alone: another tab may still be in use, and the server expires an
  // idle cookie by itself.
  useEffect(() => {
    if (!signedIn) return
    startActivityTracking(() => {
      cancelTokenTimers()
      disconnectSocket()
      useAuthStore.getState().clearAuth()
      window.location.href = '/login?reason=idle'
    })
    return stopActivityTracking
  }, [signedIn])

  // Apply theme on mount
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
  }, [theme])

  return (
    <>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<Navigate to="/overview" replace />} />
        <Route
          path="/overview"
          element={
            <ProtectedRoute isRestoring={isRestoring}>
              <OverviewPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/incidents"
          element={
            <ProtectedRoute isRestoring={isRestoring}>
              <IncidentListPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/incidents/:id"
          element={
            <ProtectedRoute isRestoring={isRestoring}>
              <IncidentWorkspacePage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/incidents/:id/:section"
          element={
            <ProtectedRoute isRestoring={isRestoring}>
              <IncidentWorkspacePage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/integrations"
          element={<Navigate to="/admin/integrations" replace />}
        />
        <Route
          path="/admin/sso"
          element={<Navigate to="/admin/integrations?section=identity" replace />}
        />
        <Route
          path="/admin"
          element={<Navigate to="/admin/org" replace />}
        />
        <Route
          path="/settings"
          element={
            <ProtectedRoute isRestoring={isRestoring}>
              <SettingsPageWrapper />
            </ProtectedRoute>
          }
        />
        <Route
          path="/report-templates"
          element={
            <ProtectedRoute isRestoring={isRestoring}>
              <ReportTemplateListPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/report-templates/:id"
          element={
            <ProtectedRoute isRestoring={isRestoring}>
              <ReportTemplateEditorPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/:section"
          element={
            <ProtectedRoute isRestoring={isRestoring}>
              <Suspense fallback={<PageLoader />}>
                <AdminPage />
              </Suspense>
            </ProtectedRoute>
          }
        />
        <Route
          path="/invite/:token"
          element={
            <Suspense fallback={<PageLoader />}>
              <InviteAcceptPage />
            </Suspense>
          }
        />
        <Route path="*" element={<Navigate to="/overview" replace />} />
      </Routes>

      <ToastContainer />
    </>
  )
}
