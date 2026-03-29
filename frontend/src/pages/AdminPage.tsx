import { useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { AppShell } from '@/components/layout/AppShell'
import { OrgSettingsPage } from '@/components/admin/OrgSettingsPage'
import { StoragePage } from '@/components/admin/StoragePage'
import { IncidentTemplatesPage } from '@/components/admin/IncidentTemplatesPage'
import { AuditLogPage } from '@/components/admin/AuditLogPage'
import { IntegrationsPage } from '@/components/integrations/IntegrationsPage'
import { ReportsAdminPage } from '@/components/admin/ReportsAdminPage'

type AdminSection = 'org' | 'storage' | 'templates' | 'reports' | 'integrations' | 'audit'

const VALID_SECTIONS: AdminSection[] = ['org', 'storage', 'templates', 'reports', 'integrations', 'audit']

export default function AdminPage() {
  const { section } = useParams<{ section?: string }>()
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)

  useEffect(() => {
    if (user && user.role !== 'admin') {
      navigate('/incidents', { replace: true })
    }
  }, [user, navigate])

  // Legacy redirects
  useEffect(() => {
    if (section === 'team') navigate('/admin/org', { replace: true })
    if (section === 'sso') navigate('/admin/integrations?section=identity', { replace: true })
  }, [section, navigate])

  if (!user || user.role !== 'admin') return null

  const activeSection: AdminSection = VALID_SECTIONS.includes(section as AdminSection)
    ? (section as AdminSection)
    : 'org'

  return (
    <AppShell>
      {activeSection === 'org' && <OrgSettingsPage />}
      {activeSection === 'storage' && <StoragePage />}
      {activeSection === 'templates' && <IncidentTemplatesPage />}
      {activeSection === 'reports' && <ReportsAdminPage />}
      {activeSection === 'integrations' && <IntegrationsPage />}
      {activeSection === 'audit' && <AuditLogPage />}
    </AppShell>
  )
}
