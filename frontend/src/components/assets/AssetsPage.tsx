import { useState } from 'react'
import {
  useAssets,
  useCreateAsset,
  useBulkCreateAssets,
  useUpdateAsset,
  useDeleteAsset,
  useAssetLinks,
  useCreateAssetLink,
  useDeleteAssetLink,
} from '@/hooks/useAssets'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { EmptyState } from '@/components/common/EmptyState'
import { Button } from '@/components/common/Button'
import { Modal } from '@/components/common/Modal'
import { useUIStore } from '@/stores/uiStore'
import {
  ASSET_TYPE_ICONS,
  ASSET_TYPE_LABELS,
  ASSET_STATUS_COLORS,
  ASSET_CRITICALITY_COLORS,
  ASSET_LINK_TYPE_LABELS,
  ASSET_TYPES_LIST,
  ASSET_LINK_TYPES_LIST,
  type Asset,
  type AssetType,
  type AssetStatus,
  type AssetCriticality,
  type AssetLinkType,
} from '@/types/asset'

interface AssetsPageProps {
  incidentId: string
}

type SubTab = 'list' | 'relationships'

// ── Asset Row ─────────────────────────────────────────────────────────────────

function AssetRow({
  asset,
  onEdit,
  onDelete,
}: {
  asset: Asset
  onEdit: (a: Asset) => void
  onDelete: (a: Asset) => void
}) {
  return (
    <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
      <td style={{ padding: '10px 12px', width: 28 }}>
        <span style={{ fontSize: 16 }}>{ASSET_TYPE_ICONS[asset.asset_type as AssetType] ?? '📦'}</span>
      </td>
      <td style={{ padding: '10px 12px' }}>
        <span style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: 13 }}>
          {asset.name}
        </span>
        {asset.description && (
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
            {asset.description}
          </div>
        )}
      </td>
      <td style={{ padding: '10px 12px' }}>
        <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
          {ASSET_TYPE_LABELS[asset.asset_type as AssetType] ?? asset.asset_type}
        </span>
      </td>
      <td style={{ padding: '10px 12px' }}>
        <span className={`chip ${ASSET_STATUS_COLORS[asset.status as AssetStatus] ?? 'chip-muted'}`}
          style={{ fontSize: 11 }}>
          {asset.status}
        </span>
      </td>
      <td style={{ padding: '10px 12px' }}>
        <span className={`chip ${ASSET_CRITICALITY_COLORS[asset.criticality as AssetCriticality] ?? 'chip-muted'}`}
          style={{ fontSize: 11 }}>
          {asset.criticality}
        </span>
      </td>
      <td style={{ padding: '10px 12px' }}>
        {asset.tags.length > 0 && (
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
            {asset.tags.map(tag => (
              <span key={tag} className="chip chip-muted" style={{ fontSize: 10 }}>{tag}</span>
            ))}
          </div>
        )}
      </td>
      <td style={{ padding: '10px 12px', textAlign: 'right' }}>
        <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
          <button
            onClick={() => onEdit(asset)}
            className="icon-btn"
            title="Edit asset"
            style={{ fontSize: 13 }}
          >✏️</button>
          <button
            onClick={() => onDelete(asset)}
            className="icon-btn"
            title="Delete asset"
            style={{ fontSize: 13 }}
          >🗑️</button>
        </div>
      </td>
    </tr>
  )
}

// ── Relationship Row ──────────────────────────────────────────────────────────

function RelationshipRow({
  link,
  assets,
  onDelete,
}: {
  link: { id: string; source_id: string; target_id: string; link_type: string; label: string | null }
  assets: Asset[]
  onDelete: (id: string) => void
}) {
  const source = assets.find(a => a.id === link.source_id)
  const target = assets.find(a => a.id === link.target_id)
  if (!source || !target) return null

  return (
    <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
      <td style={{ padding: '10px 12px' }}>
        <span style={{ fontSize: 14 }}>{ASSET_TYPE_ICONS[source.asset_type as AssetType]}</span>
        {' '}
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
          {source.name}
        </span>
      </td>
      <td style={{ padding: '10px 12px', textAlign: 'center' }}>
        <span className="chip chip-blue" style={{ fontSize: 11 }}>
          {link.label || ASSET_LINK_TYPE_LABELS[link.link_type as AssetLinkType] || link.link_type}
        </span>
      </td>
      <td style={{ padding: '10px 12px' }}>
        <span style={{ fontSize: 14 }}>{ASSET_TYPE_ICONS[target.asset_type as AssetType]}</span>
        {' '}
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
          {target.name}
        </span>
      </td>
      <td style={{ padding: '10px 12px', textAlign: 'right' }}>
        <button
          onClick={() => onDelete(link.id)}
          className="icon-btn"
          title="Remove relationship"
          style={{ fontSize: 13 }}
        >🗑️</button>
      </td>
    </tr>
  )
}

// ── Main Component ────────────────────────────────────────────────────────────

export function AssetsPage({ incidentId }: AssetsPageProps) {
  const addToast = useUIStore(s => s.addToast)
  const [subTab, setSubTab] = useState<SubTab>('list')

  const { data: assets = [], isLoading } = useAssets(incidentId)
  const { data: assetLinks = [] } = useAssetLinks(incidentId)
  const createAsset = useCreateAsset(incidentId)
  const bulkCreate = useBulkCreateAssets(incidentId)
  const updateAsset = useUpdateAsset(incidentId)
  const deleteAsset = useDeleteAsset(incidentId)
  const createLink = useCreateAssetLink(incidentId)
  const deleteLink = useDeleteAssetLink(incidentId)

  // Add form state
  const [assetType, setAssetType] = useState<AssetType>('host')
  const [namesInput, setNamesInput] = useState('')
  const [status, setStatus] = useState<AssetStatus>('suspected')
  const [criticality, setCriticality] = useState<AssetCriticality>('medium')
  const [description, setDescription] = useState('')

  // Edit modal state
  const [editingAsset, setEditingAsset] = useState<Asset | null>(null)
  const [editName, setEditName] = useState('')
  const [editStatus, setEditStatus] = useState<AssetStatus>('suspected')
  const [editCriticality, setEditCriticality] = useState<AssetCriticality>('medium')
  const [editDescription, setEditDescription] = useState('')

  // Link form state
  const [linkSource, setLinkSource] = useState('')
  const [linkTarget, setLinkTarget] = useState('')
  const [linkType, setLinkType] = useState<AssetLinkType>('communicates_with')
  const [linkLabel, setLinkLabel] = useState('')

  // Delete confirm
  const [deletingAsset, setDeletingAsset] = useState<Asset | null>(null)

  async function handleAdd() {
    const names = namesInput.split('\n').map(n => n.trim()).filter(Boolean)
    if (names.length === 0) return

    try {
      if (names.length === 1) {
        await createAsset.mutateAsync({
          asset_type: assetType,
          name: names[0],
          description: description || null,
          status,
          criticality,
          tags: [],
          metadata: {},
        })
      } else {
        await bulkCreate.mutateAsync({
          asset_type: assetType,
          names,
          description: description || null,
          status,
          criticality,
          tags: [],
        })
      }
      setNamesInput('')
      setDescription('')
      addToast(`${names.length} asset${names.length > 1 ? 's' : ''} added`, 'success')
    } catch {
      addToast('Failed to add asset(s)', 'error')
    }
  }

  function openEdit(asset: Asset) {
    setEditingAsset(asset)
    setEditName(asset.name)
    setEditStatus(asset.status as AssetStatus)
    setEditCriticality(asset.criticality as AssetCriticality)
    setEditDescription(asset.description ?? '')
  }

  async function handleSaveEdit() {
    if (!editingAsset) return
    try {
      await updateAsset.mutateAsync({
        assetId: editingAsset.id,
        payload: {
          name: editName,
          status: editStatus,
          criticality: editCriticality,
          description: editDescription || null,
        },
      })
      setEditingAsset(null)
      addToast('Asset updated', 'success')
    } catch {
      addToast('Failed to update asset', 'error')
    }
  }

  async function handleDeleteConfirm() {
    if (!deletingAsset) return
    try {
      await deleteAsset.mutateAsync(deletingAsset.id)
      setDeletingAsset(null)
      addToast('Asset deleted', 'success')
    } catch {
      addToast('Failed to delete asset', 'error')
    }
  }

  async function handleCreateLink() {
    if (!linkSource || !linkTarget || linkSource === linkTarget) return
    try {
      await createLink.mutateAsync({
        source_id: linkSource,
        target_id: linkTarget,
        link_type: linkType,
        label: linkLabel || undefined,
      })
      setLinkSource('')
      setLinkTarget('')
      setLinkLabel('')
      addToast('Relationship created', 'success')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      addToast(msg ?? 'Failed to create relationship', 'error')
    }
  }

  async function handleDeleteLink(linkId: string) {
    try {
      await deleteLink.mutateAsync(linkId)
      addToast('Relationship removed', 'success')
    } catch {
      addToast('Failed to remove relationship', 'error')
    }
  }

  if (isLoading) return <LoadingSpinner />

  const subtabStyle = (t: SubTab): React.CSSProperties => ({
    padding: '6px 14px',
    borderRadius: 8,
    border: 'none',
    background: subTab === t ? 'var(--accent-dim)' : 'transparent',
    color: subTab === t ? 'var(--accent)' : 'var(--text-muted)',
    cursor: 'pointer',
    fontSize: 13,
    fontFamily: 'Syne, sans-serif',
    fontWeight: 600,
  })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 0, height: '100%' }}>
      {/* Sub-tab bar */}
      <div style={{
        display: 'flex',
        gap: 4,
        padding: '12px 20px',
        borderBottom: '1px solid var(--border)',
        background: 'var(--bg-surface)',
        flexShrink: 0,
      }}>
        <button style={subtabStyle('list')} onClick={() => setSubTab('list')}>
          Assets {assets.length > 0 && <span style={{ opacity: 0.6 }}>({assets.length})</span>}
        </button>
        <button style={subtabStyle('relationships')} onClick={() => setSubTab('relationships')}>
          Relationships {assetLinks.length > 0 && <span style={{ opacity: 0.6 }}>({assetLinks.length})</span>}
        </button>
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: '20px' }}>
        {subTab === 'list' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {/* Add asset form */}
            <div style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: 12,
              padding: 16,
            }}>
              <div style={{ fontWeight: 700, fontSize: 13, color: 'var(--text-primary)', marginBottom: 12 }}>
                Add Assets
              </div>
              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'flex-start' }}>
                <div className="select-wrap" style={{ flex: '0 0 160px' }}>
                  <select
                    className="form-input"
                    value={assetType}
                    onChange={e => setAssetType(e.target.value as AssetType)}
                  >
                    {ASSET_TYPES_LIST.map(t => (
                      <option key={t} value={t}>
                        {ASSET_TYPE_ICONS[t]} {ASSET_TYPE_LABELS[t]}
                      </option>
                    ))}
                  </select>
                </div>

                <textarea
                  className="form-input"
                  placeholder="Asset name(s) — one per line for bulk add"
                  value={namesInput}
                  onChange={e => setNamesInput(e.target.value)}
                  rows={2}
                  style={{ flex: '1 1 220px', resize: 'vertical', minHeight: 60 }}
                />

                <input
                  className="form-input"
                  placeholder="Description (optional)"
                  value={description}
                  onChange={e => setDescription(e.target.value)}
                  style={{ flex: '1 1 180px' }}
                />

                <div className="select-wrap" style={{ flex: '0 0 130px' }}>
                  <select
                    className="form-input"
                    value={status}
                    onChange={e => setStatus(e.target.value as AssetStatus)}
                  >
                    <option value="suspected">Suspected</option>
                    <option value="confirmed">Confirmed</option>
                    <option value="remediated">Remediated</option>
                    <option value="cleared">Cleared</option>
                  </select>
                </div>

                <div className="select-wrap" style={{ flex: '0 0 120px' }}>
                  <select
                    className="form-input"
                    value={criticality}
                    onChange={e => setCriticality(e.target.value as AssetCriticality)}
                  >
                    <option value="critical">Critical</option>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                  </select>
                </div>

                <Button
                  variant="accent"
                  onClick={handleAdd}
                  disabled={!namesInput.trim() || createAsset.isPending || bulkCreate.isPending}
                >
                  Add
                </Button>
              </div>
            </div>

            {/* Asset table */}
            {assets.length === 0 ? (
              <EmptyState
                icon="🖥️"
                title="No assets yet"
                description="Add hosts, accounts, files, and other assets involved in this incident."
              />
            ) : (
              <div style={{
                background: 'var(--bg-card)',
                border: '1px solid var(--border)',
                borderRadius: 12,
                overflow: 'hidden',
              }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ background: 'var(--bg-surface)', borderBottom: '1px solid var(--border)' }}>
                      {['', 'Name', 'Type', 'Status', 'Criticality', 'Tags', ''].map((h, i) => (
                        <th key={i} style={{
                          padding: '8px 12px',
                          textAlign: 'left',
                          fontSize: 11,
                          fontWeight: 700,
                          color: 'var(--text-muted)',
                          textTransform: 'uppercase',
                          letterSpacing: '0.05em',
                        }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {assets.map(asset => (
                      <AssetRow
                        key={asset.id}
                        asset={asset}
                        onEdit={openEdit}
                        onDelete={setDeletingAsset}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {subTab === 'relationships' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {/* Link creation form */}
            <div style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: 12,
              padding: 16,
            }}>
              <div style={{ fontWeight: 700, fontSize: 13, color: 'var(--text-primary)', marginBottom: 12 }}>
                Link Assets
              </div>
              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
                <div className="select-wrap" style={{ flex: '1 1 180px' }}>
                  <select
                    className="form-input"
                    value={linkSource}
                    onChange={e => setLinkSource(e.target.value)}
                  >
                    <option value="">Source asset…</option>
                    {assets.map(a => (
                      <option key={a.id} value={a.id}>
                        {ASSET_TYPE_ICONS[a.asset_type as AssetType]} {a.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="select-wrap" style={{ flex: '0 0 180px' }}>
                  <select
                    className="form-input"
                    value={linkType}
                    onChange={e => setLinkType(e.target.value as AssetLinkType)}
                  >
                    {ASSET_LINK_TYPES_LIST.map(lt => (
                      <option key={lt} value={lt}>{ASSET_LINK_TYPE_LABELS[lt]}</option>
                    ))}
                  </select>
                </div>

                <div className="select-wrap" style={{ flex: '1 1 180px' }}>
                  <select
                    className="form-input"
                    value={linkTarget}
                    onChange={e => setLinkTarget(e.target.value)}
                  >
                    <option value="">Target asset…</option>
                    {assets.filter(a => a.id !== linkSource).map(a => (
                      <option key={a.id} value={a.id}>
                        {ASSET_TYPE_ICONS[a.asset_type as AssetType]} {a.name}
                      </option>
                    ))}
                  </select>
                </div>

                <input
                  className="form-input"
                  placeholder="Custom label (optional)"
                  value={linkLabel}
                  onChange={e => setLinkLabel(e.target.value)}
                  style={{ flex: '1 1 140px' }}
                />

                <Button
                  variant="accent"
                  onClick={handleCreateLink}
                  disabled={!linkSource || !linkTarget || createLink.isPending}
                >
                  Link
                </Button>
              </div>
              {assets.length < 2 && (
                <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 8 }}>
                  Add at least 2 assets to create relationships.
                </p>
              )}
            </div>

            {/* Relationships table */}
            {assetLinks.length === 0 ? (
              <EmptyState
                icon="🔗"
                title="No relationships yet"
                description="Link assets together to map how they're connected — e.g. account → workstation → file."
              />
            ) : (
              <div style={{
                background: 'var(--bg-card)',
                border: '1px solid var(--border)',
                borderRadius: 12,
                overflow: 'hidden',
              }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ background: 'var(--bg-surface)', borderBottom: '1px solid var(--border)' }}>
                      {['Source', 'Relationship', 'Target', ''].map((h, i) => (
                        <th key={i} style={{
                          padding: '8px 12px',
                          textAlign: i === 1 ? 'center' : 'left',
                          fontSize: 11,
                          fontWeight: 700,
                          color: 'var(--text-muted)',
                          textTransform: 'uppercase',
                          letterSpacing: '0.05em',
                        }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {assetLinks.map(link => (
                      <RelationshipRow
                        key={link.id}
                        link={link}
                        assets={assets}
                        onDelete={handleDeleteLink}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Edit modal */}
      {editingAsset && (
        <Modal title="Edit Asset" onClose={() => setEditingAsset(null)}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div>
              <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
                Name
              </label>
              <input
                className="form-input"
                value={editName}
                onChange={e => setEditName(e.target.value)}
                style={{ width: '100%' }}
              />
            </div>
            <div>
              <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
                Description
              </label>
              <textarea
                className="form-input"
                value={editDescription}
                onChange={e => setEditDescription(e.target.value)}
                rows={3}
                style={{ width: '100%', resize: 'vertical' }}
              />
            </div>
            <div style={{ display: 'flex', gap: 10 }}>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
                  Status
                </label>
                <div className="select-wrap">
                  <select
                    className="form-input"
                    value={editStatus}
                    onChange={e => setEditStatus(e.target.value as AssetStatus)}
                  >
                    <option value="suspected">Suspected</option>
                    <option value="confirmed">Confirmed</option>
                    <option value="remediated">Remediated</option>
                    <option value="cleared">Cleared</option>
                  </select>
                </div>
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
                  Criticality
                </label>
                <div className="select-wrap">
                  <select
                    className="form-input"
                    value={editCriticality}
                    onChange={e => setEditCriticality(e.target.value as AssetCriticality)}
                  >
                    <option value="critical">Critical</option>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                  </select>
                </div>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 4 }}>
              <Button variant="ghost" onClick={() => setEditingAsset(null)}>Cancel</Button>
              <Button
                variant="accent"
                onClick={handleSaveEdit}
                disabled={!editName.trim() || updateAsset.isPending}
              >
                Save
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Delete confirm modal */}
      {deletingAsset && (
        <Modal title="Delete Asset" onClose={() => setDeletingAsset(null)}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
              Delete <strong style={{ color: 'var(--text-primary)' }}>{deletingAsset.name}</strong>?
              This will also remove all timeline links for this asset.
            </p>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <Button variant="ghost" onClick={() => setDeletingAsset(null)}>Cancel</Button>
              <Button variant="danger" onClick={handleDeleteConfirm} disabled={deleteAsset.isPending}>
                Delete
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}
