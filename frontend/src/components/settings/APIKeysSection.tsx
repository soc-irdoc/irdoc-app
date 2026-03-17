import { useState } from 'react'
import { useAPIKeys, useCreateAPIKey, useRevokeAPIKey } from '@/hooks/useAPIKeys'
import { Modal } from '@/components/common/Modal'
import { Button } from '@/components/common/Button'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { useUIStore } from '@/stores/uiStore'
import { AVAILABLE_SCOPES } from '@/types/apiKey'
import { formatRelative, formatDateTime } from '@/lib/utils'

export function APIKeysSection() {
  const addToast = useUIStore((s) => s.addToast)
  const { data: keys = [], isLoading } = useAPIKeys()
  const createKey = useCreateAPIKey()
  const revokeKey = useRevokeAPIKey()

  const [showCreate, setShowCreate] = useState(false)
  const [showRawKey, setShowRawKey] = useState<string | null>(null)
  const [newName, setNewName] = useState('')
  const [newScopes, setNewScopes] = useState<Set<string>>(new Set(['incidents:create']))

  async function handleCreate() {
    if (!newName.trim()) return
    try {
      const created = await createKey.mutateAsync({
        name: newName.trim(),
        scopes: Array.from(newScopes),
      })
      setShowCreate(false)
      setNewName('')
      setShowRawKey(created.raw_key)
      addToast('API key created', 'success')
    } catch {
      addToast('Failed to create API key', 'error')
    }
  }

  async function handleRevoke(keyId: string, name: string) {
    if (!confirm(`Revoke API key "${name}"? This cannot be undone.`)) return
    try {
      await revokeKey.mutateAsync(keyId)
      addToast('API key revoked', 'success')
    } catch {
      addToast('Failed to revoke key', 'error')
    }
  }

  return (
    <div
      style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderRadius: 12,
        overflow: 'hidden',
        marginBottom: 16,
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '14px 20px',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div>
          <p style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>🔑 API Keys</p>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
            Used by external tools to create cases in IRDoc.
          </p>
        </div>
        <Button variant="accent" size="sm" onClick={() => setShowCreate(true)}>
          + Create API Key
        </Button>
      </div>

      {/* Key list */}
      {isLoading ? (
        <div className="flex justify-center py-8">
          <LoadingSpinner size="sm" />
        </div>
      ) : keys.length === 0 ? (
        <div style={{ padding: 20, fontSize: 13, color: 'var(--text-muted)' }}>
          No API keys yet. Create one to allow external tools to connect.
        </div>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr>
              {['Name', 'Prefix', 'Scopes', 'Last Used', 'Actions'].map((h) => (
                <th
                  key={h}
                  style={{
                    textAlign: 'left',
                    padding: '10px 20px',
                    color: 'var(--text-muted)',
                    fontSize: 11,
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px',
                    borderBottom: '1px solid var(--border)',
                    background: 'var(--bg-elevated)',
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {keys.map((key) => (
              <tr key={key.id}>
                <td
                  style={{
                    padding: '12px 20px',
                    borderBottom: '1px solid var(--border-subtle)',
                    fontWeight: 600,
                    color: 'var(--text-primary)',
                  }}
                >
                  {key.name}
                </td>
                <td
                  style={{
                    padding: '12px 20px',
                    borderBottom: '1px solid var(--border-subtle)',
                    fontFamily: 'JetBrains Mono, monospace',
                    color: 'var(--accent)',
                    fontSize: 11,
                  }}
                >
                  {key.key_prefix}…
                </td>
                <td
                  style={{
                    padding: '12px 20px',
                    borderBottom: '1px solid var(--border-subtle)',
                  }}
                >
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    {key.scopes.map((s) => (
                      <span key={s} className="chip chip-blue" style={{ fontSize: 10 }}>
                        {s}
                      </span>
                    ))}
                  </div>
                </td>
                <td
                  style={{
                    padding: '12px 20px',
                    borderBottom: '1px solid var(--border-subtle)',
                    color: 'var(--text-muted)',
                  }}
                >
                  {key.last_used_at ? formatRelative(key.last_used_at) : 'Never'}
                </td>
                <td
                  style={{
                    padding: '12px 20px',
                    borderBottom: '1px solid var(--border-subtle)',
                  }}
                >
                  <Button
                    variant="danger"
                    size="sm"
                    onClick={() => handleRevoke(key.id, key.name)}
                    loading={revokeKey.isPending}
                  >
                    Revoke
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* Create Key Modal */}
      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Create API Key">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <label
              style={{
                fontSize: 11,
                fontWeight: 600,
                color: 'var(--text-muted)',
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
                marginBottom: 6,
                display: 'block',
              }}
            >
              Key Name
            </label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. SDP Integration, Automation Script..."
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              autoFocus
            />
          </div>
          <div>
            <label
              style={{
                fontSize: 11,
                fontWeight: 600,
                color: 'var(--text-muted)',
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
                marginBottom: 10,
                display: 'block',
              }}
            >
              Scopes
            </label>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {AVAILABLE_SCOPES.map((scope) => (
                <label
                  key={scope.value}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    cursor: 'pointer',
                    fontSize: 13,
                    color: 'var(--text-primary)',
                  }}
                >
                  <input
                    type="checkbox"
                    checked={newScopes.has(scope.value)}
                    onChange={(e) => {
                      const next = new Set(newScopes)
                      if (e.target.checked) next.add(scope.value)
                      else next.delete(scope.value)
                      setNewScopes(next)
                    }}
                  />
                  <span>
                    <span
                      style={{
                        fontFamily: 'JetBrains Mono, monospace',
                        fontSize: 11,
                        color: 'var(--accent)',
                      }}
                    >
                      {scope.value}
                    </span>
                    {' — '}
                    {scope.label}
                  </span>
                </label>
              ))}
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <Button variant="ghost" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button
              variant="accent"
              onClick={handleCreate}
              loading={createKey.isPending}
              disabled={!newName.trim() || newScopes.size === 0}
            >
              Create Key
            </Button>
          </div>
        </div>
      </Modal>

      {/* Raw Key Display Modal — shown ONCE after creation */}
      <Modal
        open={!!showRawKey}
        onClose={() => setShowRawKey(null)}
        title="API Key Created"
      >
        <div
          style={{
            background: 'var(--yellow-dim)',
            border: '1px solid var(--yellow)',
            borderRadius: 8,
            padding: 12,
            marginBottom: 16,
            fontSize: 13,
            color: 'var(--yellow)',
          }}
        >
          ⚠️ This key will not be shown again. Copy it now.
        </div>
        <div
          style={{
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border)',
            borderRadius: 8,
            padding: 12,
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 13,
            color: 'var(--accent)',
            wordBreak: 'break-all',
            marginBottom: 16,
          }}
        >
          {showRawKey}
        </div>
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <Button
            variant="accent"
            onClick={() => {
              if (showRawKey) navigator.clipboard.writeText(showRawKey)
              addToast('Copied to clipboard', 'success')
            }}
          >
            Copy Key
          </Button>
          <Button variant="ghost" onClick={() => setShowRawKey(null)}>Done</Button>
        </div>
      </Modal>
    </div>
  )
}
