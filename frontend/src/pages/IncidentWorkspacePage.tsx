import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useIncident } from '@/hooks/useIncident'
import { AppShell } from '@/components/layout/AppShell'
import { TopBar } from '@/components/layout/TopBar'
import { TasksPanel } from '@/components/layout/TasksPanel'
import { TimelinePage } from '@/components/timeline/TimelinePage'
import { IOCPage } from '@/components/ioc/IOCPage'
import { SummaryPage } from '@/components/summary/SummaryPage'
import ReportPage from '@/components/reports/ReportPage'
import { IntegrationsPage } from '@/components/integrations/IntegrationsPage'
import { PageLoader } from '@/components/common/LoadingSpinner'
import { lazy, Suspense } from 'react'

const InvestigationGraph = lazy(() => import('@/components/graph/InvestigationGraph'))

type Section = 'timeline' | 'iocs' | 'summary' | 'reports' | 'integrations' | 'graph'

export function IncidentWorkspacePage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: incident, isLoading } = useIncident(id!)

  // Determine active section from URL hash or default to timeline
  const [activeSection, setActiveSection] = useState<Section>('timeline')

  function handleSectionChange(section: string) {
    setActiveSection(section as Section)
    navigate(`/incidents/${id}/${section}`, { replace: true })
  }

  if (isLoading) return <PageLoader />
  if (!incident) {
    return (
      <AppShell>
        <div
          style={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--text-muted)',
          }}
        >
          Incident not found.
        </div>
      </AppShell>
    )
  }

  return (
    <AppShell>
      <div
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          background: 'var(--bg-base)',
        }}
      >
        {/* TopBar */}
        <TopBar
          incident={incident}
          activeSection={activeSection}
          onSectionChange={handleSectionChange}
        />

        {/* Main content area + tasks panel */}
        <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
          {/* Center content */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            {activeSection === 'timeline'     && <TimelinePage incidentId={incident.id} />}
            {activeSection === 'iocs'         && <IOCPage incidentId={incident.id} />}
            {activeSection === 'summary'      && <SummaryPage incidentId={incident.id} />}
            {activeSection === 'reports'      && <ReportPage incidentId={incident.id} />}
            {activeSection === 'integrations' && <IntegrationsPage incidentId={incident.id} />}
            {activeSection === 'graph' && (
              <Suspense fallback={<PageLoader />}>
                <InvestigationGraph incidentId={incident.id} />
              </Suspense>
            )}
          </div>

          {/* Right tasks panel */}
          <TasksPanel incidentId={incident.id} />
        </div>
      </div>
    </AppShell>
  )
}
