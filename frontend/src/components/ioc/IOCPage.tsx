import { useState } from 'react'
import { useIOCs, useCreateIOC, useUpdateIOC, useDeleteIOC, useBulkImportIOCs } from '@/hooks/useIOCs'
import { detectIOCs } from '@/lib/iocDetector'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { EmptyState } from '@/components/common/EmptyState'
import { Modal } from '@/components/common/Modal'
import { Button } from '@/components/common/Button'
import { ConfidenceBar } from './ConfidenceBar'
import { useUIStore } from '@/stores/uiStore'
import apiClient from '@/lib/apiClient'
import {
  IOC_TYPE_ICONS,
  IOC_STATUS_COLORS,
  TLP_COLORS,
  type IOC,
  type IOCType,
  type IOCStatus,
  type DetectedIOC,
} from '@/types/ioc'

const IOC_TYPES: IOCType[] = ['ip', 'domain', 'email', 'url', 'hash', 'file', 'username']
const IOC_STATUSES: IOCStatus[] = ['active', 'blocked', 'remediated', 'fp']

interface IOCPageProps {
  incidentId: string
}

// ── Enrichment Panel ──────────────────────────────────────────────────────────

function EnrichmentPanel({
  iocId,
  iocType,
  enrichment,
}: {
  iocId: string
  iocType: string
  enrichment: Record<string, unknown>
}) {
  const addToast = useUIStore((s) => s.addToast)
  const [enriching, setEnriching] = useState(false)

  async function handleEnrich() {
    setEnriching(true)
    try {
      await apiClient.post(`/iocs/${iocId}/enrich`)
      addToast('Enrichment queued — results will appear shortly', 'success')
    } catch {
      addToast('Failed to queue enrichment', 'error')
    } finally {
      setEnriching(false)
    }
  }

  async function handleAINarrative() {
    try {
      await apiClient.post(`/iocs/${iocId}/ai/narrative`)
      addToast('AI narrative queued', 'success')
    } catch {
      addToast('AI narratives require premium plan', 'error')
    }
  }

  const vt = enrichment?.virustotal as Record<string, unknown> | undefined
  const abuse = enrichment?.abuseipdb as Record<string, unknown> | undefined
  const shodan = enrichment?.shodan as Record<string, unknown> | undefined
  const aiNarrative = enrichment?.ai_narrative as string | undefined
  const hasAny = vt || abuse || shodan || aiNarrative

  return (
    <div
      style={{
        padding: '12px 16px',
        background: 'var(--bg-base)',
        borderTop: '1px solid var(--border-subtle)',
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
      }}
    >
      {/* Actions row */}
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', flex: 1 }}>
          Enrichment Data
        </span>
        <button
          className="btn btn-ghost btn-sm"
          onClick={handleEnrich}
          disabled={enriching}
          style={{ fontSize: 11 }}
        >
          {enriching ? 'Queuing…' : '↻ Re-enrich'}
        </button>
        <button
          className="btn btn-ghost btn-sm"
          onClick={handleAINarrative}
          style={{ fontSize: 11 }}
        >
          ✨ AI Narrative
        </button>
      </div>

      {!hasAny ? (
        <p style={{ fontSize: 11, color: 'var(--text-muted)', fontStyle: 'italic' }}>
          No enrichment data yet. Click Re-enrich to run TI plugins.
        </p>
      ) : (
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
          {/* VirusTotal */}
          {vt && (
            <div style={{ flex: 1, minWidth: 180 }}>
              <p style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 6 }}>
                🦠 VirusTotal
              </p>
              {vt.found === false ? (
                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Not found</span>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <span style={{ fontSize: 11 }}>
                      <span style={{ color: 'var(--red)', fontWeight: 700 }}>{String(vt.malicious ?? 0)}</span>
                      <span style={{ color: 'var(--text-muted)' }}> malicious</span>
                    </span>
                    <span style={{ fontSize: 11 }}>
                      <span style={{ color: 'var(--yellow)', fontWeight: 700 }}>{String(vt.suspicious ?? 0)}</span>
                      <span style={{ color: 'var(--text-muted)' }}> suspicious</span>
                    </span>
                    <span style={{ fontSize: 11 }}>
                      <span style={{ color: 'var(--green)', fontWeight: 700 }}>{String(vt.harmless ?? 0)}</span>
                      <span style={{ color: 'var(--text-muted)' }}> harmless</span>
                    </span>
                  </div>
                  {Array.isArray(vt.categories) && (vt.categories as string[]).length > 0 && (
                    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                      {(vt.categories as string[]).slice(0, 4).map((cat) => (
                        <span key={cat} className="chip chip-red" style={{ fontSize: 10 }}>{cat}</span>
                      ))}
                    </div>
                  )}
                  {!!vt.permalink && (
                    <a
                      href={String(vt.permalink)}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ fontSize: 10, color: 'var(--accent)' }}
                    >
                      View on VirusTotal →
                    </a>
                  )}
                </div>
              )}
            </div>
          )}

          {/* AbuseIPDB */}
          {abuse && iocType === 'ip' && (
            <div style={{ flex: 1, minWidth: 160 }}>
              <p style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 6 }}>
                🚫 AbuseIPDB
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Confidence:</span>
                  <span
                    style={{
                      fontSize: 12,
                      fontWeight: 700,
                      color: Number(abuse.abuse_confidence_score) > 70
                        ? 'var(--red)'
                        : Number(abuse.abuse_confidence_score) > 30
                        ? 'var(--yellow)'
                        : 'var(--green)',
                    }}
                  >
                    {String(abuse.abuse_confidence_score)}%
                  </span>
                </div>
                {!!abuse.isp && <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>ISP: {String(abuse.isp)}</span>}
                {!!abuse.country_code && (
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    Country: {String(abuse.country_code)}
                  </span>
                )}
                {abuse.total_reports !== undefined && (
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    Reports: {String(abuse.total_reports)} from {String(abuse.num_distinct_users ?? 0)} users
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Shodan */}
          {shodan && (
            <div style={{ flex: 1, minWidth: 160 }}>
              <p style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 6 }}>
                📡 Shodan
              </p>
              {shodan.found === false ? (
                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Not found</span>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                  {Array.isArray(shodan.ports) && (shodan.ports as number[]).length > 0 && (
                    <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                      Ports: {(shodan.ports as number[]).slice(0, 8).join(', ')}
                    </span>
                  )}
                  {!!shodan.org && <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Org: {String(shodan.org)}</span>}
                  {!!shodan.country && <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Country: {String(shodan.country)}</span>}
                  {Array.isArray(shodan.vulns) && (shodan.vulns as string[]).length > 0 && (
                    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                      {(shodan.vulns as string[]).slice(0, 3).map((v) => (
                        <span key={v} className="chip chip-red" style={{ fontSize: 10 }}>{v}</span>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* AI Narrative */}
      {aiNarrative && (
        <div
          style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            borderRadius: 8,
            padding: '10px 12px',
            fontSize: 12,
            color: 'var(--text-secondary)',
            lineHeight: 1.6,
          }}
        >
          <span style={{ fontSize: 10, fontWeight: 700, color: 'var(--accent)', display: 'block', marginBottom: 4 }}>
            ✨ AI ANALYSIS
          </span>
          {aiNarrative}
        </div>
      )}
    </div>
  )
}

// ── IOC Row ───────────────────────────────────────────────────────────────────

function IOCRow({
  ioc,
  onStatusChange,
  onDelete,
}: {
  ioc: IOC
  onStatusChange: (id: string, status: IOCStatus) => void
  onDelete: (id: string) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const enrichment = (ioc.enrichment ?? {}) as Record<string, unknown>
  const vt = enrichment?.virustotal as Record<string, unknown> | undefined
  const abuse = enrichment?.abuseipdb as Record<string, unknown> | undefined
  const hasEnrichment = !!(vt || abuse || enrichment?.shodan)

  return (
    <>
      <tr
        style={{ cursor: 'pointer' }}
        onClick={() => setExpanded((v) => !v)}
        onMouseEnter={(e) => {
          e.currentTarget.querySelectorAll('td').forEach(
            (td) => ((td as HTMLElement).style.background = 'var(--bg-elevated)')
          )
        }}
        onMouseLeave={(e) => {
          e.currentTarget.querySelectorAll('td').forEach(
            (td) => ((td as HTMLElement).style.background = 'transparent')
          )
        }}
      >
        {/* Type */}
        <td style={{ padding: '10px 14px', borderBottom: expanded ? 'none' : '1px solid var(--border-subtle)' }}>
          <span className="chip chip-muted" style={{ fontSize: 11 }}>
            {IOC_TYPE_ICONS[ioc.ioc_type]} {ioc.ioc_type}
          </span>
        </td>

        {/* Value */}
        <td style={{ padding: '10px 14px', borderBottom: expanded ? 'none' : '1px solid var(--border-subtle)' }}>
          <span
            style={{ color: 'var(--accent)', cursor: 'copy' }}
            onClick={(e) => { e.stopPropagation(); navigator.clipboard.writeText(ioc.value) }}
            title="Click to copy"
          >
            {ioc.value.length > 55 ? ioc.value.slice(0, 55) + '…' : ioc.value}
          </span>
        </td>

        {/* Confidence + VT badge */}
        <td style={{ padding: '10px 14px', borderBottom: expanded ? 'none' : '1px solid var(--border-subtle)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <ConfidenceBar value={ioc.confidence} />
            {vt && vt.found !== false && (
              <span
                className="chip chip-red"
                style={{ fontSize: 10, padding: '1px 5px' }}
                title={`VirusTotal: ${vt.malicious} malicious`}
              >
                VT:{String(vt.malicious ?? 0)}
              </span>
            )}
            {abuse && Number(abuse.abuse_confidence_score) > 0 && (
              <span
                className={Number(abuse.abuse_confidence_score) > 70 ? 'chip chip-red' : 'chip chip-yellow'}
                style={{ fontSize: 10, padding: '1px 5px' }}
                title={`AbuseIPDB: ${abuse.abuse_confidence_score}% confidence`}
              >
                AB:{String(abuse.abuse_confidence_score)}%
              </span>
            )}
          </div>
        </td>

        {/* Status */}
        <td style={{ padding: '10px 14px', borderBottom: expanded ? 'none' : '1px solid var(--border-subtle)' }}>
          <div className="select-wrap" onClick={(e) => e.stopPropagation()}>
            <select
              className="form-input"
              value={ioc.status}
              onChange={(e) => onStatusChange(ioc.id, e.target.value as IOCStatus)}
              style={{ fontFamily: 'Syne, sans-serif', padding: '3px 24px 3px 8px', fontSize: 11, width: 'auto' }}
            >
              {IOC_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
        </td>

        {/* TLP */}
        <td style={{ padding: '10px 14px', borderBottom: expanded ? 'none' : '1px solid var(--border-subtle)' }}>
          <span className={`chip ${TLP_COLORS[ioc.tlp_level]}`} style={{ fontSize: 10 }}>
            TLP:{ioc.tlp_level.toUpperCase()}
          </span>
        </td>

        {/* Actions */}
        <td
          style={{ padding: '10px 14px', borderBottom: expanded ? 'none' : '1px solid var(--border-subtle)' }}
          onClick={(e) => e.stopPropagation()}
        >
          <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
            {hasEnrichment && (
              <span style={{ fontSize: 10, color: 'var(--green)' }} title="Enriched">●</span>
            )}
            <button
              className="icon-btn"
              onClick={() => setExpanded((v) => !v)}
              aria-label={expanded ? 'Collapse' : 'Expand enrichment'}
              style={{ fontSize: 12 }}
            >
              {expanded ? '▲' : '▼'}
            </button>
            <button
              className="icon-btn"
              onClick={() => onDelete(ioc.id)}
              aria-label="Delete IOC"
              style={{ color: 'var(--red)' }}
            >
              🗑
            </button>
          </div>
        </td>
      </tr>

      {/* Enrichment expansion row */}
      {expanded && (
        <tr>
          <td
            colSpan={6}
            style={{ borderBottom: '1px solid var(--border-subtle)', padding: 0 }}
          >
            <EnrichmentPanel
              iocId={ioc.id}
              iocType={ioc.ioc_type}
              enrichment={enrichment}
            />
          </td>
        </tr>
      )}
    </>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export function IOCPage({ incidentId }: IOCPageProps) {
  const addToast = useUIStore((s) => s.addToast)
  const { data: iocs = [], isLoading } = useIOCs(incidentId)
  const createIOC = useCreateIOC(incidentId)
  const updateIOC = useUpdateIOC(incidentId)
  const deleteIOC = useDeleteIOC(incidentId)
  const bulkImport = useBulkImportIOCs(incidentId)

  const [newType, setNewType] = useState<IOCType>('ip')
  const [newValue, setNewValue] = useState('')
  const [newConfidence, setNewConfidence] = useState(80)

  // Bulk detect modal
  const [detectText, setDetectText] = useState('')
  const [showDetectModal, setShowDetectModal] = useState(false)
  const [detectedIOCs, setDetectedIOCs] = useState<DetectedIOC[]>([])
  const [selectedIOCs, setSelectedIOCs] = useState<Set<number>>(new Set())

  function handleValuePaste(e: React.ClipboardEvent<HTMLInputElement>) {
    const text = e.clipboardData.getData('text')
    if (text.includes('\n') || text.length > 100) {
      e.preventDefault()
      setDetectText(text)
      const found = detectIOCs(text)
      if (found.length > 0) {
        setDetectedIOCs(found)
        setSelectedIOCs(new Set(found.map((_, i) => i)))
        setShowDetectModal(true)
      }
    }
  }

  async function handleAddIOC(e: React.FormEvent) {
    e.preventDefault()
    if (!newValue.trim()) return
    try {
      await createIOC.mutateAsync({ ioc_type: newType, value: newValue.trim(), confidence: newConfidence })
      setNewValue('')
      addToast('IOC added', 'success')
    } catch {
      addToast('Failed to add IOC', 'error')
    }
  }

  async function handleBulkAdd() {
    const toAdd = detectedIOCs.filter((_, i) => selectedIOCs.has(i))
    try {
      await bulkImport.mutateAsync(detectText)
      addToast(`Added ${toAdd.length} IOCs`, 'success')
      setShowDetectModal(false)
      setDetectedIOCs([])
      setDetectText('')
    } catch {
      addToast('Bulk import failed', 'error')
    }
  }

  async function handleStatusChange(iocId: string, status: IOCStatus) {
    try {
      await updateIOC.mutateAsync({ iocId, payload: { status } })
    } catch {
      addToast('Failed to update IOC', 'error')
    }
  }

  async function handleDelete(iocId: string) {
    if (!confirm('Delete this IOC?')) return
    try {
      await deleteIOC.mutateAsync(iocId)
    } catch {
      addToast('Failed to delete IOC', 'error')
    }
  }

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ flex: 1, overflowY: 'auto', padding: 24 }}>
        {/* Header */}
        <h2 style={{ fontSize: 18, fontWeight: 800, display: 'flex', alignItems: 'center', gap: 10, color: 'var(--text-primary)', marginBottom: 20 }}>
          🔍 IOCs{' '}
          <span style={{ color: 'var(--text-muted)', fontSize: 13, fontWeight: 500 }}>
            {iocs.length} indicators
          </span>
        </h2>

        {/* Add IOC form */}
        <form
          onSubmit={handleAddIOC}
          style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            borderRadius: 12,
            padding: 16,
            marginBottom: 20,
          }}
        >
          {/* Row 1: type + value */}
          <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end', flexWrap: 'wrap', marginBottom: 10 }}>
            <div className="select-wrap" style={{ minWidth: 110 }}>
              <select
                className="form-input"
                value={newType}
                onChange={(e) => setNewType(e.target.value as IOCType)}
                style={{ fontFamily: 'Syne, sans-serif' }}
              >
                {IOC_TYPES.map((t) => (
                  <option key={t} value={t}>{IOC_TYPE_ICONS[t]} {t}</option>
                ))}
              </select>
            </div>
            <input
              type="text"
              className="form-input"
              placeholder="IOC value — paste multi-line text to auto-detect..."
              value={newValue}
              onChange={(e) => setNewValue(e.target.value)}
              onPaste={handleValuePaste}
              style={{ flex: 1, minWidth: 200 }}
            />
          </div>
          {/* Row 2: confidence + submit */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <label style={{
                fontSize: 11,
                fontWeight: 600,
                color: 'var(--text-muted)',
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
              }}>
                Confidence (0–100)
              </label>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <input
                  type="range"
                  min={0} max={100} step={5}
                  value={newConfidence}
                  onChange={(e) => setNewConfidence(Number(e.target.value))}
                  style={{ width: 140, accentColor: 'var(--accent)' }}
                />
                <span style={{
                  fontSize: 13,
                  fontWeight: 700,
                  color: newConfidence >= 70 ? 'var(--green)' : newConfidence >= 40 ? 'var(--yellow)' : 'var(--red)',
                  fontFamily: 'JetBrains Mono, monospace',
                  minWidth: 36,
                }}>
                  {newConfidence}%
                </span>
              </div>
            </div>
            <div style={{ flex: 1 }} />
            <Button type="submit" variant="accent" size="sm" loading={createIOC.isPending}>
              + Add IOC
            </Button>
          </div>
        </form>

        {/* IOC Table */}
        {isLoading ? (
          <div className="flex justify-center py-12"><LoadingSpinner /></div>
        ) : iocs.length === 0 ? (
          <EmptyState icon="🔍" title="No IOCs yet" description="Add indicators above or paste multi-line text for auto-detection." />
        ) : (
          <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }}>
              <thead>
                <tr>
                  {['Type', 'Value', 'Confidence / Intel', 'Status', 'TLP', 'Actions'].map((h) => (
                    <th key={h} style={{ textAlign: 'left', padding: '10px 14px', color: 'var(--text-muted)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.5px', borderBottom: '1px solid var(--border)', background: 'var(--bg-elevated)' }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {iocs.map((ioc) => (
                  <IOCRow
                    key={ioc.id}
                    ioc={ioc}
                    onStatusChange={handleStatusChange}
                    onDelete={handleDelete}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Auto-detect modal */}
      <Modal
        open={showDetectModal}
        onClose={() => setShowDetectModal(false)}
        title={`Auto-detected ${detectedIOCs.length} IOC${detectedIOCs.length !== 1 ? 's' : ''}`}
      >
        <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 16 }}>
          Select IOCs to add to this incident:
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 20 }}>
          {detectedIOCs.map((ioc, idx) => (
            <label
              key={idx}
              style={{
                display: 'flex', alignItems: 'center', gap: 12, padding: '8px 12px',
                borderRadius: 8, cursor: 'pointer',
                background: selectedIOCs.has(idx) ? 'var(--accent-dim)' : 'var(--bg-elevated)',
                border: `1px solid ${selectedIOCs.has(idx) ? 'var(--accent)' : 'var(--border)'}`,
              }}
            >
              <input
                type="checkbox"
                checked={selectedIOCs.has(idx)}
                onChange={(e) => {
                  const next = new Set(selectedIOCs)
                  if (e.target.checked) next.add(idx)
                  else next.delete(idx)
                  setSelectedIOCs(next)
                }}
              />
              <span className="chip chip-muted" style={{ fontSize: 10 }}>{IOC_TYPE_ICONS[ioc.ioc_type]} {ioc.ioc_type}</span>
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: 'var(--text-primary)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {ioc.value}
              </span>
            </label>
          ))}
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
          <Button variant="ghost" onClick={() => setShowDetectModal(false)}>Cancel</Button>
          <Button variant="accent" onClick={handleBulkAdd} loading={bulkImport.isPending} disabled={selectedIOCs.size === 0}>
            Add {selectedIOCs.size} IOC{selectedIOCs.size !== 1 ? 's' : ''}
          </Button>
        </div>
      </Modal>
    </div>
  )
}
