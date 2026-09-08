/**
 * Inline config panel that expands below a selected canvas block.
 * Shows different fields depending on the block type.
 */
import { ReportBlock } from '@/types/report'

interface Props {
  block: ReportBlock
  onChange: (updated: Partial<ReportBlock>) => void
}

const TIMELINE_FILTER_OPTIONS = [
  { value: 'all', label: 'All entries' },
  { value: 'type=detection', label: 'Detection events only' },
  { value: 'type=analysis', label: 'Analysis entries only' },
  { value: 'type=containment', label: 'Containment actions only' },
  { value: 'type=evidence', label: 'Evidence entries only' },
  { value: 'type=comms', label: 'Communication entries only' },
  { value: 'type=note', label: 'Notes only' },
]

const IOC_FILTER_OPTIONS = [
  { value: 'all', label: 'All IOCs' },
  { value: 'status=active', label: 'Active only' },
  { value: 'status=blocked', label: 'Blocked only' },
  { value: 'status=remediated', label: 'Remediated only' },
]

const IOC_COLUMN_OPTIONS = ['type', 'value', 'description', 'status', 'confidence', 'first_seen']

const TASK_FILTER_OPTIONS = [
  { value: 'all', label: 'All tasks' },
  { value: 'phase=1', label: 'Phase 1 tasks' },
  { value: 'phase=2', label: 'Phase 2 tasks' },
  { value: 'phase=3', label: 'Phase 3 tasks' },
]

const STAT_OPTIONS = [
  { value: 'severity', label: 'Severity' },
  { value: 'status', label: 'Status' },
  { value: 'duration', label: 'Duration' },
  { value: 'affected_users', label: 'Affected Users' },
  { value: 'ioc_count', label: 'IOC Count' },
  { value: 'entry_count', label: 'Timeline Events' },
  { value: 'opened_at', label: 'Opened At' },
  { value: 'contained_at', label: 'Contained At' },
  { value: 'closed_at', label: 'Closed At' },
]

const SECTION_FIELD_OPTIONS = [
  { value: 'incident.executive_summary', label: 'Executive Summary' },
  { value: 'incident.attack_vector', label: 'Attack Vector' },
  { value: 'incident.metadata.notes', label: 'Analyst Notes' },
  { value: 'incident.metadata.root_cause', label: 'Root Cause' },
  { value: 'incident.metadata.affected_data', label: 'Affected Data / Systems' },
  { value: 'incident.metadata.regulatory_notes', label: 'Regulatory Notes' },
  { value: 'incident.metadata.preventive_actions', label: 'Preventive Actions' },
  { value: 'ai.executive_summary', label: 'AI Executive Summary' },
  { value: 'ai.recommendations', label: 'AI Recommendations' },
]

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '6px 10px',
  background: 'var(--bg-base)',
  border: '1px solid var(--border)',
  borderRadius: '6px',
  color: 'var(--text-primary)',
  fontSize: '12px',
}

const rowStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '4px',
}

const labelStyle: React.CSSProperties = {
  fontSize: '11px',
  fontWeight: 600,
  color: 'var(--text-secondary)',
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
}

export default function BlockConfigPanel({ block, onChange }: Props) {
  const { type } = block

  const renderLabelField = () => (
    <div style={rowStyle}>
      <span style={labelStyle}>Label</span>
      <input
        style={inputStyle}
        value={block.label ?? ''}
        onChange={(e) => onChange({ label: e.target.value })}
        placeholder="Section label"
      />
    </div>
  )

  if (type === 'cover') {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        <div style={rowStyle}>
          <span style={labelStyle}>Watermark text</span>
          <input
            style={inputStyle}
            value={block.watermark ?? 'CONFIDENTIAL'}
            onChange={(e) => onChange({ watermark: e.target.value })}
            placeholder="e.g. CONFIDENTIAL"
          />
        </div>
      </div>
    )
  }

  if (type === 'header') {
    return (
      <div style={rowStyle}>
        <span style={labelStyle}>Heading text</span>
        <input
          style={inputStyle}
          value={block.text ?? ''}
          onChange={(e) => onChange({ text: e.target.value })}
          placeholder="Section heading"
        />
      </div>
    )
  }

  if (type === 'section' || type === 'text_block') {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {renderLabelField()}
        <div style={rowStyle}>
          <span style={labelStyle}>Field</span>
          <select
            style={inputStyle}
            value={block.field ?? ''}
            onChange={(e) => onChange({ field: e.target.value })}
          >
            <option value="">— Select field —</option>
            {SECTION_FIELD_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
      </div>
    )
  }

  if (type === 'stat_row') {
    const current = block.stats ?? []
    return (
      <div style={rowStyle}>
        <span style={labelStyle}>Stats to show</span>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '4px' }}>
          {STAT_OPTIONS.map((s) => {
            const checked = current.includes(s.value)
            return (
              <label
                key={s.value}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '5px',
                  cursor: 'pointer',
                  fontSize: '12px',
                  color: 'var(--text-primary)',
                  padding: '3px 8px',
                  background: checked ? 'var(--accent-dim)' : 'var(--bg-base)',
                  border: `1px solid ${checked ? 'var(--accent)' : 'var(--border)'}`,
                  borderRadius: '4px',
                }}
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={(e) => {
                    const next = e.target.checked
                      ? [...current, s.value]
                      : current.filter((v) => v !== s.value)
                    onChange({ stats: next })
                  }}
                  style={{ width: '12px', height: '12px' }}
                />
                {s.label}
              </label>
            )
          })}
        </div>
      </div>
    )
  }

  if (type === 'timeline') {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {renderLabelField()}
        <div style={rowStyle}>
          <span style={labelStyle}>Filter</span>
          <select
            style={inputStyle}
            value={block.filter ?? 'all'}
            onChange={(e) => onChange({ filter: e.target.value })}
          >
            {TIMELINE_FILTER_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
        <div style={{ display: 'flex', gap: '16px' }}>
          <div style={rowStyle}>
            <span style={labelStyle}>Max entries (0 = all)</span>
            <input
              type="number"
              style={{ ...inputStyle, width: '90px' }}
              value={block.max_entries ?? 0}
              min={0}
              onChange={(e) => onChange({ max_entries: Number(e.target.value) })}
            />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '14px' }}>
            <input
              type="checkbox"
              id={`show-att-${block.id}`}
              checked={block.show_attachments ?? true}
              onChange={(e) => onChange({ show_attachments: e.target.checked })}
            />
            <label htmlFor={`show-att-${block.id}`} style={{ fontSize: '12px', color: 'var(--text-primary)' }}>
              Show attachments
            </label>
          </div>
        </div>
      </div>
    )
  }

  if (type === 'ioc_table') {
    const currentCols = block.columns ?? ['type', 'value', 'status']
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {renderLabelField()}
        <div style={rowStyle}>
          <span style={labelStyle}>Filter</span>
          <select
            style={inputStyle}
            value={block.filter ?? 'all'}
            onChange={(e) => onChange({ filter: e.target.value })}
          >
            {IOC_FILTER_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
        <div style={rowStyle}>
          <span style={labelStyle}>Columns</span>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
            {IOC_COLUMN_OPTIONS.map((col) => {
              const checked = currentCols.includes(col)
              return (
                <label
                  key={col}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer',
                    fontSize: '12px', padding: '3px 8px',
                    background: checked ? 'var(--accent-dim)' : 'var(--bg-base)',
                    border: `1px solid ${checked ? 'var(--accent)' : 'var(--border)'}`,
                    borderRadius: '4px', color: 'var(--text-primary)',
                  }}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={(e) => {
                      const next = e.target.checked
                        ? [...currentCols, col]
                        : currentCols.filter((c) => c !== col)
                      onChange({ columns: next })
                    }}
                    style={{ width: '12px', height: '12px' }}
                  />
                  {col.replace('_', ' ')}
                </label>
              )
            })}
          </div>
        </div>
      </div>
    )
  }

  if (type === 'task_list') {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {renderLabelField()}
        <div style={rowStyle}>
          <span style={labelStyle}>Filter</span>
          <select
            style={inputStyle}
            value={block.filter ?? 'all'}
            onChange={(e) => onChange({ filter: e.target.value })}
          >
            {TASK_FILTER_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
        <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', cursor: 'pointer', color: 'var(--text-primary)' }}>
          <input
            type="checkbox"
            checked={block.show_completed ?? true}
            onChange={(e) => onChange({ show_completed: e.target.checked })}
          />
          Show completed tasks
        </label>
      </div>
    )
  }

  if (type === 'evidence_register') {
    return renderLabelField()
  }

  if (type === 'tag_list') {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {renderLabelField()}
        <div style={rowStyle}>
          <span style={labelStyle}>Field</span>
          <select
            style={inputStyle}
            value={block.field ?? 'incident.attack_vector'}
            onChange={(e) => onChange({ field: e.target.value })}
          >
            <option value="incident.attack_vector">Attack Vector</option>
            <option value="incident.external_refs">External References</option>
          </select>
        </div>
      </div>
    )
  }

  // divider, page_break — no config
  return (
    <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
      No configuration for this block type.
    </div>
  )
}
