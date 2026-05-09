import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useIncident } from '@/hooks/useIncident'
import { joinIncident, leaveIncident } from '@/lib/websocket'
import { AppShell } from '@/components/layout/AppShell'
import { TopBar } from '@/components/layout/TopBar'
import { TasksPanel } from '@/components/layout/TasksPanel'
import { TimelinePage } from '@/components/timeline/TimelinePage'
import { IOCPage } from '@/components/ioc/IOCPage'
import { AssetsPage } from '@/components/assets/AssetsPage'
import { SummaryPage } from '@/components/summary/SummaryPage'
import ReportPage from '@/components/reports/ReportPage'
import { PageLoader } from '@/components/common/LoadingSpinner'
import { lazy, Suspense } from 'react'

const InvestigationGraph = lazy(() => import('@/components/graph/InvestigationGraph'))

type Section = 'timeline' | 'iocs' | 'assets' | 'summary' | 'reports' | 'graph'

const VALID_SECTIONS: Section[] = ['timeline', 'iocs', 'assets', 'summary', 'reports', 'graph']

export function IncidentWorkspacePage() {
  const { id, section } = useParams<{ id: string; section?: string }>()
  const navigate = useNavigate()
  const { data: incident, isLoading } = useIncident(id!)

  useEffect(() => {
    if (!id) return
    joinIncident(id)
    return () => leaveIncident(id)
  }, [id])

  // Initialize from URL section param, fall back to timeline
  const [activeSection, setActiveSection] = useState<Section>(() => {
    const s = section as Section
    return VALID_SECTIONS.includes(s) ? s : 'timeline'
  })

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
            {activeSection === 'timeline' && <TimelinePage incidentId={incident.id} />}
            {activeSection === 'iocs'     && <IOCPage incidentId={incident.id} />}
            {activeSection === 'assets'   && <AssetsPage incidentId={incident.id} />}
            {activeSection === 'summary'  && <SummaryPage incidentId={incident.id} />}
            {activeSection === 'reports'  && <ReportPage incidentId={incident.id} />}
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
