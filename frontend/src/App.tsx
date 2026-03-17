import { useEffect, lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import axios from 'axios'
import { useAuthStore } from '@/stores/authStore'
import { useThemeStore } from '@/stores/themeStore'
import { ToastContainer } from '@/components/common/Toast'
import { LoginPage } from '@/pages/LoginPage'
import { IncidentListPage } from '@/pages/IncidentListPage'
import { IncidentWorkspacePage } from '@/pages/IncidentWorkspacePage'
import { SettingsPageWrapper } from '@/pages/SettingsPageWrapper'
import { IntegrationsPageWrapper } from '@/pages/IntegrationsPageWrapper'
import { PageLoader } from '@/components/common/LoadingSpinner'
import ReportTemplateListPage from '@/pages/ReportTemplateListPage'
import ReportTemplateEditorPage from '@/pages/ReportTemplateEditorPage'

const AdminPage = lazy(() => import('@/pages/AdminPage'))
const InviteAcceptPage = lazy(() => import('@/pages/InviteAcceptPage'))

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user)
  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}

export function App() {
  const { setAuth } = useAuthStore()
  const { theme } = useThemeStore()

  // Restore session on load by hitting /auth/refresh with the refresh cookie
  useEffect(() => {
    async function tryRestore() {
      try {
        // Use plain axios (not apiClient) to avoid the 401 interceptor triggering
        // a full-page redirect here, which would cause an infinite reload loop.
        const refreshRes = await axios.post('/api/v1/auth/refresh', {}, { withCredentials: true })
        const token = refreshRes.data.data.access_token
        setAuth(refreshRes.data.user, token)
      } catch {
        // No session — user will be redirected to login by ProtectedRoute
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
            <ProtectedRoute>
              <IncidentListPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/incidents/:id"
          element={
            <ProtectedRoute>
              <IncidentWorkspacePage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/incidents/:id/:section"
          element={
            <ProtectedRoute>
              <IncidentWorkspacePage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/integrations"
          element={
            <ProtectedRoute>
              <IntegrationsPageWrapper />
            </ProtectedRoute>
          }
        />
        <Route
          path="/settings"
          element={
            <ProtectedRoute>
              <SettingsPageWrapper />
            </ProtectedRoute>
          }
        />
        <Route
          path="/report-templates"
          element={
            <ProtectedRoute>
              <ReportTemplateListPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/report-templates/:id"
          element={
            <ProtectedRoute>
              <ReportTemplateEditorPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin"
          element={
            <ProtectedRoute>
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
