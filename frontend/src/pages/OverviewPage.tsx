import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { PieChart, Pie, Cell, Tooltip } from 'recharts'
import { useAuthStore } from '@/stores/authStore'
import { useDashboardStats } from '@/hooks/useDashboardStats'
import { getTimeRange, TIME_RANGE_LABELS, type TimeRangeOption } from '@/utils/timeRange'
import { ProgressBar } from '@/components/common/ProgressBar'
import { EmptyState } from '@/components/common/EmptyState'
import { AppShell } from '@/components/layout/AppShell'
import type { DashboardStats } from '@/types/dashboard'

// ── Color maps ────────────────────────────────────────────────────────────────
const STATUS_COLORS: Record<string, string> = {
  open: '#58a6ff',
  monitoring: '#e3b341',
  contained: '#f85149',
  closed: '#3fb950',
}
const SEV_COLORS: Record<string, string> = {
  sev1: '#f85149',
  sev2: '#e3b341',
  sev3: '#58a6ff',
  sev4: '#3fb950',
}
const SEV_LABELS: Record<string, string> = {
  sev1: 'Sev 1', sev2: 'Sev 2', sev3: 'Sev 3', sev4: 'Sev 4',
}
const PRIORITY_COLORS: Record<string, string> = {
  critical: '#f85149', high: '#e3b341', medium: '#58a6ff', low: '#3fb950',
}
const VECTOR_COLORS = ['#f85149', '#e3b341', '#bc8cff', '#58a6ff', '#3fb950']

const TOOLTIP_STYLE = {
  background: 'var(--bg-surface)',
  border: '1px solid var(--border)',
  borderRadius: 6,
  fontSize: 13,
  color: 'var(--text-primary)',
}

// ── Shared primitives ─────────────────────────────────────────────────────────
function Tile({ children, accent = false, style = {} }: {
  children: React.ReactNode
  accent?: boolean
  style?: React.CSSProperties
}) {
  return (
    <div style={{
      background: 'var(--bg-card)',
      border: `1px solid ${accent ? 'rgba(249,115,22,0.35)' : 'var(--border)'}`,
      borderLeft: accent ? '2px solid var(--accent)' : undefined,
      borderRadius: 10,
      padding: '18px 20px',
      display: 'flex',
      flexDirection: 'column',
      gap: 6,
      overflow: 'hidden',
      ...style,
    }}>
      {children}
    </div>
  )
}

function SectionLabel({ children, accent = false }: { children: React.ReactNode; accent?: boolean }) {
  return (
    <div style={{
      fontSize: 13,
      fontWeight: 700,
      textTransform: 'uppercase',
      letterSpacing: '0.08em',
      color: accent ? 'var(--accent)' : 'var(--text-muted)',
      marginBottom: 2,
    }}>
      {children}
    </div>
  )
}

function ItemRow({ children, onClick }: { children: React.ReactNode; onClick?: () => void }) {
  const base: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '4px 0',
    borderBottom: '1px solid var(--border-subtle)',
    width: '100%',
    textAlign: 'left',
  }
  if (onClick) {
    return (
      <button onClick={onClick} style={{ ...base, background: 'none', border: 'none', borderBottom: '1px solid var(--border-subtle)', cursor: 'pointer' }}>
        {children}
      </button>
    )
  }
  return <div style={base}>{children}</div>
}

function SevChip({ severity }: { severity: string }) {
  const color = SEV_COLORS[severity] ?? '#484f58'
  return (
    <span style={{
      background: `${color}22`,
      color,
      borderRadius: 3,
      padding: '2px 6px',
      fontSize: 12,
      fontWeight: 700,
      flexShrink: 0,
      textTransform: 'uppercase',
    }}>
      {severity}
    </span>
  )
}

function IncidentTitle({ title }: { title: string }) {
  return (
    <span style={{ flex: 1, fontSize: 13, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
      {title}
    </span>
  )
}

function Ago({ iso }: { iso: string }) {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  const label = mins < 60 ? `${mins}m` : mins < 1440 ? `${Math.floor(mins / 60)}h` : `${Math.floor(mins / 1440)}d`
  return <span style={{ fontSize: 13, color: 'var(--text-muted)', flexShrink: 0 }}>{label} ago</span>
}

function StatRow({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 13 }}>
      <span style={{ color: 'var(--text-muted)' }}>{label}</span>
      <span style={{ fontWeight: 600, color: color ?? 'var(--text-primary)' }}>{value}</span>
    </div>
  )
}

function SkeletonTile() {
  return (
    <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
      <div style={{
        height: '100%',
        background: 'linear-gradient(90deg, var(--bg-card) 25%, var(--bg-elevated) 50%, var(--bg-card) 75%)',
        backgroundSize: '200% 100%',
        animation: 'shimmer 1.4s infinite',
      }} />
    </div>
  )
}

// ── Tiles ─────────────────────────────────────────────────────────────────────
function StatusDonutTile({ data }: { data: DashboardStats }) {
  const chartData = Object.entries(data.incidents.by_status)
    .map(([k, v]) => ({ name: k, value: v, color: STATUS_COLORS[k] ?? '#484f58' }))
    .filter((d) => d.value > 0)
  const total = chartData.reduce((s, d) => s + d.value, 0)

  return (
    <Tile>
      <SectionLabel>Status</SectionLabel>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', gap: 14 }}>
        <div style={{ position: 'relative', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          <PieChart width={200} height={200}>
            <Pie data={chartData} cx="50%" cy="50%" innerRadius={72} outerRadius={92} dataKey="value" stroke="none">
              {chartData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
            </Pie>
            <Tooltip contentStyle={TOOLTIP_STYLE} />
          </PieChart>
          <div style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            textAlign: 'center',
            pointerEvents: 'none',
          }}>
            <div style={{ fontSize: 38, fontWeight: 700, color: 'var(--text-primary)', lineHeight: 1 }}>{total}</div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 3 }}>cases</div>
          </div>
        </div>
        <div style={{ fontSize: 11, lineHeight: 2, alignSelf: 'stretch' }}>
          {Object.entries(data.incidents.by_status).map(([k, v]) => (
            <div key={k} style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: STATUS_COLORS[k] ?? 'var(--text-muted)' }}>● {k}</span>
              <span style={{ color: 'var(--text-secondary)' }}>{v}</span>
            </div>
          ))}
        </div>
      </div>
    </Tile>
  )
}

function SeverityDonutTile({ data }: { data: DashboardStats }) {
  const chartData = Object.entries(data.incidents.by_severity)
    .map(([k, v]) => ({ name: k, value: v, color: SEV_COLORS[k] ?? '#484f58' }))
    .filter((d) => d.value > 0)

  return (
    <Tile>
      <SectionLabel>Severity</SectionLabel>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', gap: 14 }}>
        <div style={{ position: 'relative', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          <PieChart width={190} height={190}>
            <Pie data={chartData} cx="50%" cy="50%" innerRadius={66} outerRadius={86} dataKey="value" stroke="none">
              {chartData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
            </Pie>
            <Tooltip contentStyle={TOOLTIP_STYLE} />
          </PieChart>
          <div style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            textAlign: 'center',
            pointerEvents: 'none',
          }}>
            <div style={{ fontSize: 38, fontWeight: 700, color: 'var(--text-primary)', lineHeight: 1 }}>
              {data.incidents.total}
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 3 }}>total</div>
          </div>
        </div>
        <div style={{ alignSelf: 'stretch' }}>
          {Object.entries(data.incidents.by_severity).map(([k, v]) => (
            <div key={k} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 4 }}>
              <span style={{ color: SEV_COLORS[k] }}>■ {SEV_LABELS[k]}</span>
              <span style={{ color: 'var(--text-secondary)' }}>{v}</span>
            </div>
          ))}
        </div>
      </div>
    </Tile>
  )
}

function RecentCasesTile({ data }: { data: DashboardStats }) {
  const navigate = useNavigate()
  const incidents = data.incidents.recent

  return (
    <Tile>
      <SectionLabel>Recent Cases</SectionLabel>
      {incidents.length === 0
        ? <div style={{ color: 'var(--text-muted)', fontSize: 14 }}>No recent cases</div>
        : incidents.map((inc) => (
          <ItemRow key={inc.id} onClick={() => navigate(`/incidents/${inc.id}`)}>
            <SevChip severity={inc.severity} />
            <IncidentTitle title={inc.title} />
            <Ago iso={inc.created_at} />
          </ItemRow>
        ))
      }
    </Tile>
  )
}

function TeamWorkloadTile({ data }: { data: DashboardStats }) {
  const workload = data.team_workload
  const maxCount = Math.max(...workload.map((w) => w.open_count), 1)

  return (
    <Tile>
      <SectionLabel>Team Workload — Open Cases</SectionLabel>
      {workload.length === 0
        ? <div style={{ color: 'var(--text-muted)', fontSize: 14 }}>No active assignments</div>
        : <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 4 }}>
            {workload.map((member) => {
              const pct = Math.round((member.open_count / maxCount) * 100)
              const color = pct >= 80 ? '#f85149' : pct >= 50 ? '#e3b341' : '#3fb950'
              return (
                <div key={member.user_id} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{ width: 72, fontSize: 13, color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flexShrink: 0 }}>
                    {member.full_name.split(' ')[0]}
                  </div>
                  <div style={{ flex: 1 }}>
                    <ProgressBar value={pct} color={color} />
                  </div>
                  <div style={{ width: 18, fontSize: 12, color: 'var(--text-muted)', textAlign: 'right', flexShrink: 0 }}>
                    {member.open_count}
                  </div>
                </div>
              )
            })}
          </div>
      }
    </Tile>
  )
}

function MyTasksTile({ data }: { data: DashboardStats }) {
  const navigate = useNavigate()
  const stats = data.my_stats

  return (
    <Tile accent>
      <SectionLabel accent>My Tasks</SectionLabel>
      {!stats || stats.recent_tasks.length === 0
        ? <div style={{ color: 'var(--text-muted)', fontSize: 14 }}>No pending tasks</div>
        : <>
            {stats.recent_tasks.map((task) => (
              <ItemRow key={task.id} onClick={() => navigate(`/incidents/${task.incident_id}/tasks`)}>
                <div style={{ width: 6, height: 6, borderRadius: '50%', background: PRIORITY_COLORS[task.priority] ?? '#484f58', flexShrink: 0 }} />
                <IncidentTitle title={task.title} />
                <span style={{ fontSize: 11, color: 'var(--text-muted)', flexShrink: 0 }}>{task.incident_ref}</span>
              </ItemRow>
            ))}
            <div style={{ marginTop: 'auto', paddingTop: 6, display: 'flex', gap: 12, alignItems: 'center' }}>
              <div style={{ fontSize: 26, fontWeight: 700, color: 'var(--accent)', lineHeight: 1 }}>{stats.pending_tasks}</div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.6 }}>
                pending tasks<br />across {stats.assigned_count} case{stats.assigned_count !== 1 ? 's' : ''}
              </div>
            </div>
          </>
      }
    </Tile>
  )
}

function MyCasesTile({ data }: { data: DashboardStats }) {
  const navigate = useNavigate()
  const led = data.led_cases

  return (
    <Tile accent>
      <SectionLabel accent>Cases I Lead</SectionLabel>
      {led?.recent.map((inc) => (
        <ItemRow key={inc.id} onClick={() => navigate(`/incidents/${inc.id}`)}>
          <SevChip severity={inc.severity} />
          <IncidentTitle title={inc.title} />
        </ItemRow>
      ))}
      <div style={{ marginTop: 'auto', paddingTop: 6, display: 'flex' }}>
        {[
          { value: led?.count ?? 0, label: 'led', color: 'var(--purple)' },
          { value: data.resolved_count, label: 'resolved', color: '#3fb950' },
          { value: led?.unassigned_count ?? 0, label: led?.unassigned_count ? 'unassigned!' : 'unassigned', color: led?.unassigned_count ? '#f85149' : 'var(--text-muted)' },
        ].map(({ value, label, color }) => (
          <div key={label} style={{ flex: 1, textAlign: 'center' }}>
            <div style={{ fontSize: 18, fontWeight: 700, color, lineHeight: 1 }}>{value}</div>
            <div style={{ fontSize: 11, color, marginTop: 2 }}>{label}</div>
          </div>
        ))}
      </div>
    </Tile>
  )
}

function AttackVectorsTile({ data }: { data: DashboardStats }) {
  const vectors = data.attack_vectors ?? []
  const maxCount = Math.max(...vectors.map((v) => v.count), 1)

  return (
    <Tile accent>
      <SectionLabel accent>Top Attack Vectors</SectionLabel>
      {vectors.length === 0
        ? <div style={{ color: 'var(--text-muted)', fontSize: 14 }}>No data in this period</div>
        : <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 4 }}>
            {vectors.map((v, i) => (
              <div key={v.vector} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={{ width: 72, fontSize: 13, color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flexShrink: 0, textTransform: 'capitalize' }}>
                  {v.vector}
                </div>
                <div style={{ flex: 1 }}>
                  <ProgressBar value={Math.round((v.count / maxCount) * 100)} color={VECTOR_COLORS[i % VECTOR_COLORS.length]} />
                </div>
                <div style={{ width: 18, fontSize: 12, color: 'var(--text-muted)', textAlign: 'right', flexShrink: 0 }}>{v.count}</div>
              </div>
            ))}
          </div>
      }
    </Tile>
  )
}

function OrgHealthTile({ data }: { data: DashboardStats }) {
  const health = data.org_health
  if (!health) return null
  const mfaPct = health.active_users > 0 ? Math.round((health.mfa_enabled_count / health.active_users) * 100) : 0

  return (
    <Tile accent>
      <SectionLabel accent>Org Health</SectionLabel>
      <StatRow label="Active users" value={String(health.active_users)} />
      <StatRow
        label="MFA enabled"
        value={`${health.mfa_enabled_count} / ${health.active_users}`}
        color={mfaPct < 80 ? '#e3b341' : '#3fb950'}
      />
      <ProgressBar value={mfaPct} color={mfaPct < 80 ? '#e3b341' : '#3fb950'} />
      <StatRow
        label="Pending invites"
        value={String(health.pending_invites)}
        color={health.pending_invites > 0 ? '#58a6ff' : undefined}
      />
      <StatRow
        label="Integrations"
        value={`${health.active_integrations} / ${health.total_integrations}`}
      />
    </Tile>
  )
}

function UserActivityTile({ data }: { data: DashboardStats }) {
  const audit = data.recent_audit ?? []

  return (
    <Tile accent>
      <SectionLabel accent>Recent Activity</SectionLabel>
      {audit.length === 0
        ? <div style={{ color: 'var(--text-muted)', fontSize: 14 }}>No recent activity</div>
        : audit.map((entry, i) => (
          <ItemRow key={i}>
            <span style={{
              background: 'var(--bg-elevated)',
              color: 'var(--text-muted)',
              borderRadius: 3,
              padding: '1px 5px',
              fontSize: 10,
              fontWeight: 600,
              flexShrink: 0,
            }}>
              {entry.action.split('.').pop()}
            </span>
            <span style={{ flex: 1, fontSize: 12, color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {entry.user_email}
            </span>
            <Ago iso={entry.created_at} />
          </ItemRow>
        ))
      }
    </Tile>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────
export function OverviewPage() {
  const user = useAuthStore((s) => s.user)
  const [range, setRange] = useState<TimeRangeOption>('30d')
  const { from_dt, to_dt } = useMemo(() => getTimeRange(range), [range])
  const { data, isLoading, isError } = useDashboardStats(from_dt, to_dt)
  const isAdmin = user?.role === 'admin'
  const TILE_H = 440

  return (
    <AppShell>
      <div style={{ padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: 12, flex: 1, overflowY: 'auto' }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'Syne, sans-serif' }}>
              Overview
            </div>
            {user?.full_name && (
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                Welcome back, {user.full_name.split(' ')[0]}
              </div>
            )}
          </div>
          <select
            value={range}
            onChange={(e) => setRange(e.target.value as TimeRangeOption)}
            style={{
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border)',
              borderRadius: 6,
              padding: '5px 10px',
              fontSize: 12,
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              outline: 'none',
            }}
          >
            {(Object.keys(TIME_RANGE_LABELS) as TimeRangeOption[]).map((opt) => (
              <option key={opt} value={opt}>{TIME_RANGE_LABELS[opt]}</option>
            ))}
          </select>
        </div>

        {isError && (
          <div style={{ padding: '12px 16px', background: 'var(--red-dim)', border: '1px solid rgba(248,81,73,0.3)', borderRadius: 8, fontSize: 13, color: 'var(--red)' }}>
            Failed to load dashboard stats. Please refresh.
          </div>
        )}

        {isLoading && (
          <>
            <div style={{ display: 'grid', gridTemplateColumns: '120px 160px 1fr', gap: 10, height: TILE_H }}>
              <SkeletonTile /><SkeletonTile /><SkeletonTile />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: isAdmin ? '1fr 1fr 1fr' : '2fr 1fr', gap: 10, height: TILE_H }}>
              <SkeletonTile /><SkeletonTile />{isAdmin && <SkeletonTile />}
            </div>
          </>
        )}

        {!isLoading && data && (
          data.incidents.total === 0 && range !== 'all'
            ? <EmptyState
                icon="bar_chart_color.svg"
                title="No incidents in this period"
                description="Try expanding the time range or check back later."
                action={
                  <button
                    onClick={() => setRange('all')}
                    style={{
                      padding: '8px 16px',
                      background: 'var(--accent)',
                      color: '#fff',
                      border: 'none',
                      borderRadius: 6,
                      fontSize: 13,
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    View all time
                  </button>
                }
              />
            : <>
                {/* Row 1: status donut | severity donut | recent cases */}
                <div style={{ display: 'grid', gridTemplateColumns: '250px 250px 1fr', gap: 10, height: TILE_H }}>
                  <StatusDonutTile data={data} />
                  <SeverityDonutTile data={data} />
                  <RecentCasesTile data={data} />
                </div>

                {/* Row 2: team workload + role-specific */}
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: isAdmin ? '1fr 1fr 1fr' : '2fr 1fr',
                  gap: 10,
                  height: TILE_H,
                }}>
                  <TeamWorkloadTile data={data} />
                  {isAdmin ? (
                    <>
                      <OrgHealthTile data={data} />
                      <UserActivityTile data={data} />
                    </>
                  ) : user?.role === 'senior_analyst' ? (
                    <MyCasesTile data={data} />
                  ) : user?.role === 'viewer' ? (
                    <AttackVectorsTile data={data} />
                  ) : (
                    <MyTasksTile data={data} />
                  )}
                </div>
              </>
        )}
      </div>

      <style>{`
        @keyframes shimmer {
          0%   { background-position: -200% 0; }
          100% { background-position:  200% 0; }
        }
      `}</style>
    </AppShell>
  )
}
