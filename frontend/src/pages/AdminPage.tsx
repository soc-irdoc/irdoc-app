import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { AdminShell } from '@/components/admin/AdminShell'
import { TeamPage } from '@/components/admin/TeamPage'
import { OrgSettingsPage } from '@/components/admin/OrgSettingsPage'
import { StoragePage } from '@/components/admin/StoragePage'
import { IncidentTemplatesPage } from '@/components/admin/IncidentTemplatesPage'
import { AuditLogPage } from '@/components/admin/AuditLogPage'
import { SSOPage } from '@/components/admin/SSOPage'
import { IntegrationsPage } from '@/components/integrations/IntegrationsPage'
import { ReportsAdminPage } from '@/components/admin/ReportsAdminPage'

type AdminTab = 'team' | 'org' | 'storage' | 'templates' | 'reports' | 'integrations' | 'audit' | 'sso'

export default function AdminPage() {
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const [activeTab, setActiveTab] = useState<AdminTab>('team')

  // Redirect non-admins
  useEffect(() => {
    if (user && user.role !== 'admin') {
      navigate('/incidents', { replace: true })
    }
  }, [user, navigate])

  if (!user || user.role !== 'admin') return null

  return (
    <AdminShell activeTab={activeTab} onTabChange={setActiveTab}>
      {activeTab === 'team' && <TeamPage />}
      {activeTab === 'org' && <OrgSettingsPage />}
      {activeTab === 'storage' && <StoragePage />}
      {activeTab === 'templates' && <IncidentTemplatesPage />}
      {activeTab === 'reports' && <ReportsAdminPage />}
      {activeTab === 'integrations' && <IntegrationsPage />}
      {activeTab === 'audit' && <AuditLogPage />}
      {activeTab === 'sso' && <SSOPage />}
    </AdminShell>
  )
}
