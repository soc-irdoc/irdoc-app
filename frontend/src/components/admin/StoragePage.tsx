import { useState } from 'react'
import {
  useStorageConfig,
  useUpdateStorageConfig,
  useTestStorageConnection,
  useSwitchStorageBackend,
} from '@/hooks/useAdmin'
import { useUIStore } from '@/stores/uiStore'
import { PremiumGate } from '@/components/common/PremiumGate'

type Backend = 'local' | 's3' | 'azure_blob' | 'gcs'

interface BackendFormState {
  // S3
  s3_endpoint?: string
  s3_access_key_id?: string
  s3_secret_access_key?: string
  s3_bucket?: string
  s3_region?: string
  // Azure
  azure_account_name?: string
  azure_account_key?: string
  azure_container?: string
  // GCS
  gcs_service_account_json?: string
  gcs_bucket?: string
}

function SectionCard({
  title,
  children,
}: {
  title: string
  children: React.ReactNode
}) {
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
      <div
        style={{
          padding: '14px 20px',
          borderBottom: '1px solid var(--border)',
          fontSize: 13,
          fontWeight: 700,
          color: 'var(--text-primary)',
        }}
      >
        {title}
      </div>
      <div style={{ padding: 20 }}>{children}</div>
    </div>
  )
}

interface BackendCardProps {
  id: Backend
  label: string
  description: string
  selected: boolean
  onSelect: () => void
  children?: React.ReactNode
}

function BackendCard({ id, label, description, selected, onSelect, children }: BackendCardProps) {
  return (
    <div
      style={{
        border: `1px solid ${selected ? 'var(--accent)' : 'var(--border)'}`,
        borderRadius: 10,
        padding: 16,
        marginBottom: 12,
        background: selected ? 'var(--accent-dim)' : 'var(--bg-elevated)',
        cursor: 'pointer',
        transition: 'all 0.15s',
      }}
      onClick={onSelect}
    >
      <label
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: 10,
          cursor: 'pointer',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <input
          type="radio"
          name="storage_backend"
          checked={selected}
          onChange={onSelect}
          style={{ marginTop: 2, accentColor: 'var(--accent)' }}
        />
        <div style={{ flex: 1 }}>
          <div
            style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 2 }}
          >
            {label}
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{description}</div>
        </div>
      </label>

      {selected && children && (
        <div
          style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--border)' }}
          onClick={(e) => e.stopPropagation()}
        >
          {children}
        </div>
      )}
    </div>
  )
}

export function StoragePage() {
  const addToast = useUIStore((s) => s.addToast)
  const { data: storageConfig } = useStorageConfig()
  const testConnection = useTestStorageConnection()
  const switchBackend = useSwitchStorageBackend()

  const [selected, setSelected] = useState<Backend>(storageConfig?.backend ?? 'local')
  const [form, setForm] = useState<BackendFormState>({})
  const [testResult, setTestResult] = useState<{ ok: boolean; error: string | null } | null>(null)

  function updateForm(key: keyof BackendFormState, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }))
    setTestResult(null)
  }

  function buildPayload() {
    return { backend: selected, ...form }
  }

  async function handleTest() {
    try {
      const result = await testConnection.mutateAsync(buildPayload())
      setTestResult(result)
    } catch {
      setTestResult({ ok: false, error: 'Connection test failed' })
    }
  }

  async function handleSwitch() {
    try {
      await switchBackend.mutateAsync(buildPayload())
      addToast(`Switched to ${selected} storage`, 'success')
    } catch {
      addToast('Failed to switch storage backend', 'error')
    }
  }

  const fieldLabel = (text: string) => (
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
      {text}
    </label>
  )

  const s3Fields = (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div>
        {fieldLabel('Endpoint URL (optional)')}
        <input
          type="url"
          className="form-input"
          placeholder="https://s3.amazonaws.com"
          value={form.s3_endpoint ?? ''}
          onChange={(e) => updateForm('s3_endpoint', e.target.value)}
        />
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <div>
          {fieldLabel('Access Key ID')}
          <input
            type="text"
            className="form-input"
            placeholder="AKIAIOSFODNN7EXAMPLE"
            value={form.s3_access_key_id ?? ''}
            onChange={(e) => updateForm('s3_access_key_id', e.target.value)}
          />
        </div>
        <div>
          {fieldLabel('Secret Access Key')}
          <input
            type="password"
            className="form-input"
            placeholder="••••••••"
            value={form.s3_secret_access_key ?? ''}
            onChange={(e) => updateForm('s3_secret_access_key', e.target.value)}
          />
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <div>
          {fieldLabel('Bucket')}
          <input
            type="text"
            className="form-input"
            placeholder="my-irdoc-bucket"
            value={form.s3_bucket ?? ''}
            onChange={(e) => updateForm('s3_bucket', e.target.value)}
          />
        </div>
        <div>
          {fieldLabel('Region')}
          <input
            type="text"
            className="form-input"
            placeholder="us-east-1"
            value={form.s3_region ?? ''}
            onChange={(e) => updateForm('s3_region', e.target.value)}
          />
        </div>
      </div>
    </div>
  )

  const azureFields = (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div>
        {fieldLabel('Account Name')}
        <input
          type="text"
          className="form-input"
          placeholder="mystorageaccount"
          value={form.azure_account_name ?? ''}
          onChange={(e) => updateForm('azure_account_name', e.target.value)}
        />
      </div>
      <div>
        {fieldLabel('Account Key')}
        <input
          type="password"
          className="form-input"
          placeholder="••••••••"
          value={form.azure_account_key ?? ''}
          onChange={(e) => updateForm('azure_account_key', e.target.value)}
        />
      </div>
      <div>
        {fieldLabel('Container')}
        <input
          type="text"
          className="form-input"
          placeholder="irdoc-files"
          value={form.azure_container ?? ''}
          onChange={(e) => updateForm('azure_container', e.target.value)}
        />
      </div>
    </div>
  )

  const gcsFields = (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div>
        {fieldLabel('Service Account JSON')}
        <textarea
          className="form-input"
          placeholder={'{\n  "type": "service_account",\n  …\n}'}
          value={form.gcs_service_account_json ?? ''}
          onChange={(e) => updateForm('gcs_service_account_json', e.target.value)}
          style={{ minHeight: 120 }}
        />
      </div>
      <div>
        {fieldLabel('Bucket Name')}
        <input
          type="text"
          className="form-input"
          placeholder="my-irdoc-bucket"
          value={form.gcs_bucket ?? ''}
          onChange={(e) => updateForm('gcs_bucket', e.target.value)}
        />
      </div>
    </div>
  )

  const cloudBackendContent = (
    <>
      <BackendCard
        id="s3"
        label="Amazon S3 / S3-Compatible"
        description="Store files in AWS S3 or any S3-compatible endpoint (MinIO, Backblaze B2, etc.)"
        selected={selected === 's3'}
        onSelect={() => setSelected('s3')}
      >
        {s3Fields}
      </BackendCard>

      <BackendCard
        id="azure_blob"
        label="Azure Blob Storage"
        description="Store files in Microsoft Azure Blob Storage"
        selected={selected === 'azure_blob'}
        onSelect={() => setSelected('azure_blob')}
      >
        {azureFields}
      </BackendCard>

      <BackendCard
        id="gcs"
        label="Google Cloud Storage"
        description="Store files in Google Cloud Storage"
        selected={selected === 'gcs'}
        onSelect={() => setSelected('gcs')}
      >
        {gcsFields}
      </BackendCard>
    </>
  )

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: 24 }}>
      <h2
        style={{ fontSize: 18, fontWeight: 800, color: 'var(--text-primary)', marginBottom: 24 }}
      >
        🗄️ Storage Configuration
      </h2>

      <div style={{ maxWidth: 640 }}>
        <SectionCard title="Storage Backend">
          <BackendCard
            id="local"
            label="Local Filesystem"
            description="Store files on the server's local disk (default — suitable for single-server deployments)"
            selected={selected === 'local'}
            onSelect={() => setSelected('local')}
          />

          <div style={{ position: 'relative' }}>
            <PremiumGate featureKey="cloud_storage">
              {cloudBackendContent}
            </PremiumGate>
          </div>
        </SectionCard>

        {/* Test + Save actions */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            flexWrap: 'wrap',
          }}
        >
          <button
            className="btn btn-ghost"
            onClick={handleTest}
            disabled={testConnection.isPending}
          >
            {testConnection.isPending ? 'Testing…' : 'Test Connection'}
          </button>

          <button
            className="btn btn-accent"
            onClick={handleSwitch}
            disabled={switchBackend.isPending}
          >
            {switchBackend.isPending ? 'Switching…' : 'Save & Switch'}
          </button>

          {testResult && (
            <span
              style={{
                fontSize: 13,
                fontWeight: 600,
                color: testResult.ok ? 'var(--green)' : 'var(--red)',
              }}
            >
              {testResult.ok ? '✓ Connected' : `✗ Failed: ${testResult.error ?? 'Unknown error'}`}
            </span>
          )}
        </div>

        {/* Migration note */}
        <div
          style={{
            marginTop: 24,
            padding: '12px 16px',
            background: 'var(--yellow-dim)',
            border: '1px solid var(--yellow)',
            borderRadius: 8,
            fontSize: 12,
            color: 'var(--yellow)',
            lineHeight: 1.6,
          }}
        >
          <strong>Note:</strong> Switching backends does not migrate existing files. Old files remain
          accessible via their original backend until manually migrated.
        </div>
      </div>
    </div>
  )
}
