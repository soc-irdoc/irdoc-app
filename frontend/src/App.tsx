import { useEffect, useState, lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import axios from 'axios'
import { useAuthStore } from '@/stores/authStore'
import { scheduleTokenRefresh } from '@/lib/apiClient'
import { useThemeStore } from '@/stores/themeStore'
import { ToastContainer } from '@/components/common/Toast'
import { LoginPage } from '@/pages/LoginPage'
import { IncidentListPage } from '@/pages/IncidentListPage'
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
  const { theme } = useThemeStore()
  const [isRestoring, setIsRestoring] = useState(true)

  // Restore session on load by hitting /auth/refresh with the refresh cookie
  useEffect(() => {
    async function tryRestore() {
      try {
        // Use plain axios (not apiClient) to avoid the 401 interceptor triggering
        // a full-page redirect here, which would cause an infinite reload loop.
        const refreshRes = await axios.post('/api/v1/auth/refresh', {}, { withCredentials: true })
        const token = refreshRes.data.data.access_token
        setAuth(refreshRes.data.user, token)
        scheduleTokenRefresh(token)
      } catch {
        // No session — user will be redirected to login by ProtectedRoute
      } finally {
        setIsRestoring(false)
      }
    }
    tryRestore()
  }, [setAuth])

  // Apply theme on mount
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
  }, [theme])

  return (
    <>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<Navigate to="/incidents" replace />} />
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
        <Route path="*" element={<Navigate to="/incidents" replace />} />
      </Routes>

      <ToastContainer />
    </>
  )
}
