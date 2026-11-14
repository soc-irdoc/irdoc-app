import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { FaArrowDown, FaArrowUp, FaCopy, FaDownload, FaEye, FaFileCsv } from 'react-icons/fa6'
import { useEvidenceFiles, useEvidenceIOCs } from '@/hooks/useEvidence'
import {
  EVIDENCE_PAGE_SIZES,
  EVIDENCE_TYPE_FILTERS,
  parseEvidenceQuery,
  toEvidenceApiParams,
  toEvidenceSearchParams,
  type EvidenceQuery,
  type EvidenceSortKey,
  type EvidenceTypeFilter,
} from '@/lib/evidenceQuery'
import { previewKind } from '@/lib/preview'
import { copyToClipboard, fileSize, formatDateTime } from '@/lib/utils'
import apiClient from '@/lib/apiClient'
import { useUIStore } from '@/stores/uiStore'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { EmptyState } from '@/components/common/EmptyState'
import { Pagination } from '@/components/common/Pagination'
import { Modal } from '@/components/common/Modal'
import { Button } from '@/components/common/Button'
import { ImageLightbox } from '@/components/common/ImageLightbox'
import { PdfPreviewModal } from '@/components/common/PdfPreviewModal'
import { TextPreviewModal } from '@/components/common/TextPreviewModal'
import { ENTRY_TYPE_CONFIG, type EntryType } from '@/types/timeline'
import { TLP_COLORS, type TLPLevel } from '@/types/ioc'
import type { EvidenceFile, EvidenceSource } from '@/types/evidence'

interface EvidencePageProps {
  incidentId: string
}

const COLUMNS: Array<{ key: EvidenceSortKey; label: string }> = [
  { key: 'name', label: 'Name' },
  { key: 'source', label: 'Source' },
  { key: 'type', label: 'Type' },
  { key: 'size', label: 'Size' },
  { key: 'sha256', label: 'SHA-256' },
  { key: 'uploaded_by', label: 'Uploaded by' },
  { key: 'uploaded_at', label: 'Uploaded' },
]

const cellStyle: React.CSSProperties = {
  padding: '8px 10px',
  fontSize: 12,
  borderBottom: '1px solid var(--border)',
  verticalAlign: 'top',
  color: 'var(--text-primary)',
}

function entryLabel(src: EvidenceSource): string {
  const type = ENTRY_TYPE_CONFIG[src.entry_type as EntryType]?.label ?? src.entry_type
  return `${type} · ${formatDateTime(src.occurred_at)}`
}

async function fetchAttachmentUrl(incidentId: string, attachmentId: string): Promise<string> {
  const res = await apiClient.get<{ data: { url: string } }>(
    `/incidents/${incidentId}/attachments/${attachmentId}/url`,
  )
  return res.data.data.url
}

function triggerDownload(url: string, name: string) {
  const a = document.createElement('a')
  a.href = url
  a.download = name
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

// Read-only list of everything collected in the incident (#150). Files are
// still added on timeline entries; there is no upload or delete here.
export function EvidencePage({ incidentId }: EvidencePageProps) {
  const navigate = useNavigate()
  const addToast = useUIStore((s) => s.addToast)
  const [searchParams, setSearchParams] = useSearchParams()
  const query = useMemo(() => parseEvidenceQuery(searchParams), [searchParams])
  const [searchInput, setSearchInput] = useState(query.search)

  const files = useEvidenceFiles(incidentId, query, query.view === 'files')
  const iocs = useEvidenceIOCs(incidentId, query.view === 'iocs')

  const [lightboxUrl, setLightboxUrl] = useState<string | null>(null)
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [textPreview, setTextPreview] = useState<{
    name: string; text: string | null; truncated: boolean; loading: boolean
  } | null>(null)
  const [noPreview, setNoPreview] = useState<EvidenceFile | null>(null)
  const closeLightbox = useCallback(() => setLightboxUrl(null), [])
  const closePdf = useCallback(() => setPdfUrl(null), [])

  const updateQuery = useCallback(
    (patch: Partial<EvidenceQuery>, { replace = false } = {}) => {
      const next = { ...query, page: 1, ...patch }
      setSearchParams(toEvidenceSearchParams(next), { replace })
    },
    [query, setSearchParams],
  )

  useEffect(() => setSearchInput(query.search), [query.search])
  useEffect(() => {
    if (searchInput.trim() === query.search) return
    const t = setTimeout(() => updateQuery({ search: searchInput.trim() }, { replace: true }), 300)
    return () => clearTimeout(t)
  }, [searchInput, query.search, updateQuery])

  function handleSort(key: EvidenceSortKey) {
    const order = query.sort === key ? (query.order === 'asc' ? 'desc' : 'asc') : key === 'uploaded_at' ? 'desc' : 'asc'
    updateQuery({ sort: key, order })
  }

  async function handleDownload(file: EvidenceFile) {
    try {
      triggerDownload(await fetchAttachmentUrl(incidentId, file.id), file.original_name)
    } catch {
      addToast(`Failed to download ${file.original_name}`, 'error')
    }
  }

  async function handlePreview(file: EvidenceFile) {
    const kind = previewKind(file.mime_type)
    try {
      if (kind === 'image') setLightboxUrl(await fetchAttachmentUrl(incidentId, file.id))
      else if (kind === 'pdf') setPdfUrl(await fetchAttachmentUrl(incidentId, file.id))
      else if (kind === 'text') {
        setTextPreview({ name: file.original_name, text: null, truncated: false, loading: true })
        const res = await apiClient.get<{ data: { text: string; truncated: boolean } }>(
          `/incidents/${incidentId}/attachments/${file.id}/text`,
        )
        setTextPreview({ name: file.original_name, ...res.data.data, loading: false })
      } else setNoPreview(file)
    } catch {
      setTextPreview(null)
      addToast(`Failed to load a preview of ${file.original_name}`, 'error')
    }
  }

  async function handleExport() {
    try {
      const res = await apiClient.get(`/incidents/${incidentId}/evidence/export.csv`, {
        params: toEvidenceApiParams(query),
        responseType: 'blob',
      })
      const url = URL.createObjectURL(res.data)
      triggerDownload(url, `evidence-${incidentId}.csv`)
      URL.revokeObjectURL(url)
    } catch {
      addToast('Failed to export the evidence register', 'error')
    }
  }

  function copyHash(sha: string) {
    copyToClipboard(sha)
    addToast('SHA-256 copied', 'success')
  }

  const rows = files.data?.data ?? []
  const total = files.data?.meta?.total ?? 0
  const filtered = query.kind !== 'all' || query.type !== 'all' || query.search !== '' || query.hideScreenshots

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: 24 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>Evidence Register</h2>
        <div style={{ display: 'flex', gap: 4 }} role="tablist" aria-label="Evidence view">
          {(['files', 'iocs'] as const).map((v) => (
            <button
              key={v}
              role="tab"
              aria-selected={query.view === v}
              className={`btn btn-sm ${query.view === v ? 'btn-accent' : 'btn-ghost'}`}
              onClick={() => updateQuery({ view: v })}
            >
              {v === 'files' ? 'Files' : 'IOCs'}
            </button>
          ))}
        </div>
        {query.view === 'files' && (
          <Button variant="ghost" size="sm" onClick={handleExport} style={{ marginLeft: 'auto' }}>
            <FaFileCsv size={12} aria-hidden="true" /> Export CSV
          </Button>
        )}
      </div>

      {query.view === 'files' ? (
        <>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap', marginBottom: 12 }}>
            <input
              type="search"
              className="form-input"
              placeholder="Search name or hash..."
              aria-label="Search name or hash"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              style={{ maxWidth: 240 }}
            />
            <div className="select-wrap" style={{ maxWidth: 200 }}>
              <select
                className="form-input"
                aria-label="Filter by source"
                value={query.kind}
                onChange={(e) => updateQuery({ kind: e.target.value as EvidenceQuery['kind'] })}
              >
                <option value="all">All sources</option>
                <option value="timeline">Timeline entries</option>
                <option value="incident">Incident</option>
              </select>
            </div>
            <div className="select-wrap" style={{ maxWidth: 240 }}>
              <select
                className="form-input"
                aria-label="Filter by type"
                value={query.type}
                onChange={(e) => updateQuery({ type: e.target.value as EvidenceTypeFilter })}
              >
                {EVIDENCE_TYPE_FILTERS.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
            <label style={{ display: 'flex', gap: 6, alignItems: 'center', fontSize: 12, color: 'var(--text-secondary)' }}>
              <input
                type="checkbox"
                checked={query.hideScreenshots}
                onChange={(e) => updateQuery({ hideScreenshots: e.target.checked })}
                style={{ accentColor: 'var(--accent)' }}
              />
              Hide screenshots
            </label>
          </div>

          {files.isLoading ? (
            <div className="flex justify-center py-16"><LoadingSpinner /></div>
          ) : files.isError ? (
            <EmptyState title="Could not load the evidence register" description="You may not have access to this incident's files." />
          ) : rows.length === 0 ? (
            <EmptyState
              title={filtered ? 'No files match these filters' : 'Nothing collected yet'}
              description={filtered ? 'Change or clear the filters.' : 'Files added to timeline entries appear here.'}
            />
          ) : (
            <>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr>
                      {COLUMNS.map(({ key, label }) => {
                        const active = query.sort === key
                        const Arrow = query.order === 'asc' ? FaArrowUp : FaArrowDown
                        return (
                          <th key={key} style={{ ...cellStyle, textAlign: 'left', color: 'var(--text-muted)' }}>
                            <button
                              type="button"
                              className="incident-sort-btn"
                              data-active={active}
                              onClick={() => handleSort(key)}
                              aria-label={active ? `${label}, sorted ${query.order === 'asc' ? 'ascending' : 'descending'}. Click to reverse.` : `Sort by ${label.toLowerCase()}`}
                            >
                              {label}
                              {active && <Arrow size={9} aria-hidden="true" />}
                            </button>
                          </th>
                        )
                      })}
                      <th style={{ ...cellStyle, textAlign: 'right', color: 'var(--text-muted)' }}>
                        <span className="sr-only">Actions</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((f) => (
                      <tr key={f.id} data-testid="evidence-row">
                        <td style={cellStyle}>
                          <div style={{ fontWeight: 600, wordBreak: 'break-all' }}>{f.original_name}</div>
                          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 4 }}>
                            {f.is_screenshot && <span className="chip chip-muted" style={{ fontSize: 9 }}>SCREENSHOT</span>}
                            {(f.ioc_matches ?? []).map((m) => (
                              <button
                                key={m.id}
                                type="button"
                                className="chip chip-red"
                                style={{ fontSize: 9, cursor: 'pointer' }}
                                title={`SHA-256 matches IOC ${m.value}`}
                                onClick={() => navigate(`/incidents/${incidentId}/iocs?ioc=${m.id}`)}
                              >
                                MATCHES IOC
                              </button>
                            ))}
                          </div>
                        </td>
                        <td style={cellStyle}>
                          {f.source ? (
                            <>
                              <button
                                type="button"
                                className="link-btn"
                                style={{ background: 'none', border: 'none', padding: 0, color: 'var(--accent)', cursor: 'pointer', textAlign: 'left', fontSize: 12 }}
                                onClick={() => navigate(`/incidents/${incidentId}/timeline?entry=${f.source!.entry_id}`)}
                              >
                                {entryLabel(f.source)}
                              </button>
                              {f.source.excerpt && (
                                <div style={{ color: 'var(--text-muted)', fontSize: 11, marginTop: 2 }}>{f.source.excerpt}</div>
                              )}
                              {f.assets && f.assets.length > 0 && (
                                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 4 }}>
                                  {f.assets.map((a) => (
                                    <span key={a.id} className="chip chip-blue" style={{ fontSize: 9 }} title={a.asset_type}>{a.name}</span>
                                  ))}
                                </div>
                              )}
                              {/* IOCs seen in this entry (#152); null without IOC access */}
                              {f.linked_iocs && f.linked_iocs.length > 0 && (
                                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 4 }}>
                                  {f.linked_iocs.map((i) => (
                                    <button
                                      key={i.id}
                                      type="button"
                                      className="chip chip-red"
                                      style={{ fontSize: 9, cursor: 'pointer', border: 'none', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis' }}
                                      title={`IOC (${i.ioc_type}): ${i.value}`}
                                      onClick={() => navigate(`/incidents/${incidentId}/iocs?ioc=${i.id}`)}
                                    >
                                      {i.value}
                                    </button>
                                  ))}
                                </div>
                              )}
                            </>
                          ) : (
                            <span style={{ color: 'var(--text-secondary)' }}>Incident</span>
                          )}
                        </td>
                        <td style={{ ...cellStyle, fontFamily: 'JetBrains Mono, monospace', fontSize: 11 }}>{f.mime_type ?? 'unknown'}</td>
                        <td style={{ ...cellStyle, whiteSpace: 'nowrap' }}>{f.file_size != null ? fileSize(f.file_size) : '-'}</td>
                        <td style={{ ...cellStyle, whiteSpace: 'nowrap' }}>
                          <code title={f.sha256} style={{ fontSize: 11 }}>{f.sha256.slice(0, 12)}…</code>
                          <button type="button" className="icon-btn" onClick={() => copyHash(f.sha256)} aria-label={`Copy SHA-256 of ${f.original_name}`}>
                            <FaCopy size={11} aria-hidden="true" />
                          </button>
                        </td>
                        <td style={cellStyle}>{f.uploaded_by_name ?? '-'}</td>
                        <td style={{ ...cellStyle, whiteSpace: 'nowrap' }}>{formatDateTime(f.uploaded_at)}</td>
                        <td style={{ ...cellStyle, whiteSpace: 'nowrap', textAlign: 'right' }}>
                          <button type="button" className="icon-btn" onClick={() => handlePreview(f)} aria-label={`Preview ${f.original_name}`} title="Preview">
                            <FaEye size={13} aria-hidden="true" />
                          </button>
                          <button type="button" className="icon-btn" onClick={() => handleDownload(f)} aria-label={`Download ${f.original_name}`} title="Download">
                            <FaDownload size={13} aria-hidden="true" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <Pagination
                page={query.page}
                perPage={query.perPage}
                total={total}
                pageSizes={EVIDENCE_PAGE_SIZES}
                onPageChange={(page) => updateQuery({ page })}
                onPerPageChange={(perPage) => updateQuery({ perPage })}
              />
            </>
          )}
        </>
      ) : iocs.isLoading ? (
        <div className="flex justify-center py-16"><LoadingSpinner /></div>
      ) : iocs.isError ? (
        <EmptyState title="Could not load IOCs" description="You may not have permission to read IOCs." />
      ) : (iocs.data ?? []).length === 0 ? (
        <EmptyState title="No IOCs yet" description="IOCs added to this incident appear here." />
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              {['Type', 'Value', 'TLP', 'Timeline entries', 'Matching files'].map((h) => (
                <th key={h} style={{ ...cellStyle, textAlign: 'left', color: 'var(--text-muted)' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {(iocs.data ?? []).map((ioc) => (
              <tr key={ioc.id} data-testid="evidence-ioc-row">
                <td style={cellStyle}>{ioc.ioc_type}</td>
                <td style={{ ...cellStyle, wordBreak: 'break-all' }}>
                  <button
                    type="button"
                    style={{ background: 'none', border: 'none', padding: 0, color: 'var(--accent)', cursor: 'pointer', textAlign: 'left', fontFamily: 'JetBrains Mono, monospace', fontSize: 11 }}
                    onClick={() => navigate(`/incidents/${incidentId}/iocs?ioc=${ioc.id}`)}
                  >
                    {ioc.value}
                  </button>
                </td>
                <td style={cellStyle}>
                  <span className={`chip ${TLP_COLORS[ioc.tlp_level as TLPLevel] ?? 'chip-muted'}`} style={{ fontSize: 9 }}>
                    TLP:{ioc.tlp_level.toUpperCase()}
                  </span>
                </td>
                <td style={cellStyle}>
                  {ioc.linked_entries.length === 0 ? (
                    <span style={{ color: 'var(--text-muted)' }}>Not linked to entries</span>
                  ) : (
                    <>
                      {ioc.linked_entries.map((e) => (
                        <div key={e.entry_id}>
                          <button
                            type="button"
                            style={{ background: 'none', border: 'none', padding: 0, color: 'var(--accent)', cursor: 'pointer', fontSize: 12 }}
                            onClick={() => navigate(`/incidents/${incidentId}/timeline?entry=${e.entry_id}`)}
                          >
                            {entryLabel(e)}
                          </button>
                        </div>
                      ))}
                      <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>{ioc.file_count} file(s) on these entries</div>
                    </>
                  )}
                </td>
                <td style={cellStyle}>
                  {ioc.matching_files.length > 0 ? (
                    <button
                      type="button"
                      className="chip chip-red"
                      style={{ fontSize: 9, cursor: 'pointer' }}
                      onClick={() => updateQuery({ view: 'files', search: ioc.value.trim() })}
                    >
                      {ioc.matching_files.length} MATCHING FILE{ioc.matching_files.length > 1 ? 'S' : ''}
                    </button>
                  ) : (
                    <span style={{ color: 'var(--text-muted)' }}>-</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <ImageLightbox url={lightboxUrl} onClose={closeLightbox} />
      <PdfPreviewModal url={pdfUrl} onClose={closePdf} />
      <TextPreviewModal
        open={!!textPreview}
        title={textPreview?.name ?? ''}
        text={textPreview?.text ?? null}
        truncated={textPreview?.truncated}
        loading={textPreview?.loading}
        onClose={() => setTextPreview(null)}
      />
      {noPreview && (
        <Modal open onClose={() => setNoPreview(null)} title={noPreview.original_name}>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 12 }}>
            Preview not available for this file type ({noPreview.mime_type ?? 'unknown'}).
          </p>
          <p style={{ fontSize: 12, marginBottom: 16 }}>
            SHA-256: <code style={{ wordBreak: 'break-all' }}>{noPreview.sha256}</code>
          </p>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <Button variant="ghost" onClick={() => copyHash(noPreview.sha256)}>Copy hash</Button>
            <Button variant="accent" onClick={() => { handleDownload(noPreview); setNoPreview(null) }}>Download</Button>
          </div>
        </Modal>
      )}
    </div>
  )
}
