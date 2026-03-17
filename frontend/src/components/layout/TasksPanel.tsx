import { useTasks, useUpdateTask } from '@/hooks/useTasks'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { ProgressBar } from '@/components/common/ProgressBar'
import { PRIORITY_COLORS } from '@/types/task'
import type { Task } from '@/types/task'

interface TasksPanelProps {
  incidentId: string
}

export function TasksPanel({ incidentId }: TasksPanelProps) {
  const { data: tasks = [], isLoading } = useTasks(incidentId)
  const updateTask = useUpdateTask(incidentId)

  const done = tasks.filter((t) => t.status === 'done').length
  const progress = tasks.length > 0 ? Math.round((done / tasks.length) * 100) : 0

  // Group by phase
  const groups = tasks.reduce<Record<string, Task[]>>((acc, task) => {
    const phase = task.phase || 'General'
    if (!acc[phase]) acc[phase] = []
    acc[phase].push(task)
    return acc
  }, {})

  function toggleTask(task: Task) {
    const newStatus = task.status === 'done' ? 'pending' : 'done'
    updateTask.mutate({ taskId: task.id, payload: { status: newStatus } })
  }

  return (
    <aside
      style={{
        width: 280,
        background: 'var(--bg-surface)',
        borderLeft: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        flexShrink: 0,
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '14px 16px',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}
      >
        <h2 style={{ fontSize: 13, fontWeight: 700, flex: 1, color: 'var(--text-primary)' }}>
          Tasks
        </h2>
        <span
          style={{
            fontSize: 11,
            fontWeight: 700,
            color: 'var(--text-muted)',
            fontFamily: 'JetBrains Mono, monospace',
          }}
        >
          {done}/{tasks.length}
        </span>
      </div>

      {/* Progress bar */}
      <div style={{ padding: '8px 16px', borderBottom: '1px solid var(--border-subtle)' }}>
        <ProgressBar
          value={progress}
          color={progress === 100 ? 'var(--green)' : 'var(--accent)'}
        />
        <p style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4 }}>
          {progress}% complete
        </p>
      </div>

      {/* Task list */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '10px 12px' }}>
        {isLoading ? (
          <div className="flex justify-center py-8">
            <LoadingSpinner size="sm" />
          </div>
        ) : tasks.length === 0 ? (
          <p style={{ fontSize: 12, color: 'var(--text-muted)', padding: '16px 4px' }}>
            No tasks for this incident.
          </p>
        ) : (
          Object.entries(groups).map(([phase, phaseTasks]) => (
            <div key={phase} style={{ marginBottom: 16 }}>
              <p
                style={{
                  fontSize: 10,
                  fontWeight: 700,
                  color: 'var(--text-muted)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.8px',
                  marginBottom: 8,
                  padding: '0 4px',
                }}
              >
                {phase}
              </p>
              {phaseTasks
                .sort((a, b) => a.sort_order - b.sort_order)
                .map((task) => (
                  <div
                    key={task.id}
                    onClick={() => toggleTask(task)}
                    style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: 10,
                      padding: '9px 10px',
                      borderRadius: 8,
                      cursor: 'pointer',
                      marginBottom: 2,
                      transition: 'background 0.1s',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = 'var(--bg-elevated)'
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = 'transparent'
                    }}
                  >
                    {/* Checkbox */}
                    <div
                      style={{
                        width: 16,
                        height: 16,
                        borderRadius: 4,
                        border: `2px solid ${task.status === 'done' ? 'var(--green)' : 'var(--border)'}`,
                        background: task.status === 'done' ? 'var(--green)' : 'transparent',
                        flexShrink: 0,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        marginTop: 1,
                        transition: 'all 0.15s',
                        fontSize: 10,
                        color: '#fff',
                      }}
                    >
                      {task.status === 'done' && '✓'}
                    </div>

                    {/* Text */}
                    <span
                      style={{
                        fontSize: 12,
                        lineHeight: 1.5,
                        flex: 1,
                        textDecoration: task.status === 'done' ? 'line-through' : 'none',
                        color: task.status === 'done' ? 'var(--text-muted)' : 'var(--text-primary)',
                      }}
                    >
                      {task.title}
                    </span>

                    {/* Priority */}
                    <span
                      className={`chip ${PRIORITY_COLORS[task.priority]}`}
                      style={{ fontSize: 9, padding: '1px 5px', marginLeft: 'auto' }}
                    >
                      {task.priority.toUpperCase()}
                    </span>
                  </div>
                ))}
            </div>
          ))
        )}
      </div>
    </aside>
  )
}
