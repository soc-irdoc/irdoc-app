import { useState } from 'react'
import { useIntegrations, useSaveIntegrationConfig, useTestIntegration, useToggleIntegration } from '@/hooks/useIntegrations'
import { useUIStore } from '@/stores/uiStore'
import { ToggleSwitch } from '@/components/common/ToggleSwitch'
import PremiumGate from '@/components/common/PremiumGate'
import { Modal } from '@/components/common/Modal'
import { CATEGORY_LABELS } from '@/types/integration'
import type { Integration } from '@/types/integration'

interface IntegrationsPageProps {
  incidentId: string
}

// ── Integration Config Modal ──────────────────────────────────────────────────

function IntegrationConfigModal({
  integration,
  onClose,
}: {
  integration: Integration
  onClose: () => void
}) {
  const addToast = useUIStore((s) => s.addToast)
  const saveConfig = useSaveIntegrationConfig()
  const testConn = useTestIntegration()
  const [values, setValues] = useState<Record<string, string>>(() => {
    const defaults: Record<string, string> = {}
    for (const [key, field] of Object.entries(integration.config_schema)) {
      defaults[key] = field.default ?? ''
    }
    return defaults
  })
  const [testResult, setTestResult] = useState<{ ok: boolean; error: string | null } | null>(null)

  async function handleSave() {
    try {
      await saveConfig.mutateAsync({ pluginName: integration.name, config: values })
      addToast('Configuration saved', 'success')
      onClose()
    } catch {
      addToast('Failed to save configuration', 'error')
    }
  }

  async function handleTest() {
    try {
      const result = await testConn.mutateAsync(integration.name)
      setTestResult(result)
      if (result.ok) {
        addToast('Connection successful ✓', 'success')
      } else {
        addToast(`Connection failed: ${result.error}`, 'error')
      }
    } catch {
      addToast('Connection test failed', 'error')
    }
  }

  return (
    <Modal title={`Configure ${integration.display_name}`} onClose={onClose} maxWidth={480}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>{integration.description}</p>

        {Object.entries(integration.config_schema).map(([key, field]) => (
          <div key={key} style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)' }}>
              {field.label}
              {field.required && <span style={{ color: 'var(--accent)' }}> *</span>}
            </label>
            <input
              type={field.type === 'password' ? 'password' : 'text'}
              className="form-input"
              placeholder={field.placeholder ?? field.default ?? ''}
              value={values[key] ?? ''}
              onChange={(e) => setValues((prev) => ({ ...prev, [key]: e.target.value }))}
            />
          </div>
        ))}

        {testResult && (
          <div
            style={{
              padding: '8px 12px',
              borderRadius: 6,
              fontSize: 12,
              background: testResult.ok ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)',
              color: testResult.ok ? 'var(--green)' : 'var(--red)',
              border: `1px solid ${testResult.ok ? 'var(--green)' : 'var(--red)'}`,
            }}
          >
            {testResult.ok ? '✓ Connection successful' : `✗ ${testResult.error ?? 'Connection failed'}`}
          </div>
        )}

        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 8 }}>
          <button
            className="btn btn-ghost btn-sm"
            onClick={handleTest}
            disabled={testConn.isPending}
          >
            {testConn.isPending ? 'Testing…' : 'Test Connection'}
          </button>
          <button className="btn btn-ghost btn-sm" onClick={onClose}>Cancel</button>
          <button
            className="btn btn-accent btn-sm"
            onClick={handleSave}
            disabled={saveConfig.isPending}
          >
            {saveConfig.isPending ? 'Saving…' : 'Save'}
          </button>
        </div>
      </div>
    </Modal>
  )
}

// ── Integration Card ──────────────────────────────────────────────────────────

function IntegrationCard({ integration }: { integration: Integration }) {
  const addToast = useUIStore((s) => s.addToast)
  const toggle = useToggleIntegration()
  const [showConfig, setShowConfig] = useState(false)

  async function handleToggle(enabled: boolean) {
    if (!integration.is_configured && enabled) {
      addToast('Configure the integration first', 'info')
      setShowConfig(true)
      return
    }
    try {
      await toggle.mutateAsync({ pluginName: integration.name, enabled })
    } catch {
      addToast('Failed to toggle integration', 'error')
    }
  }

  const statusColor = integration.last_test_status === 'ok'
    ? 'var(--green)'
    : integration.last_test_status === 'fail'
    ? 'var(--red)'
    : 'var(--text-muted)'

  const statusText = !integration.is_configured
    ? 'Not configured'
    : integration.last_test_status === 'ok'
    ? 'Connected ✓'
    : integration.last_test_status === 'fail'
    ? 'Connection failed'
    : 'Configured'

  return (
    <>
      <div
        style={{
          background: 'var(--bg-surface)',
          border: `1px solid ${integration.is_enabled ? 'var(--accent)' : 'var(--border)'}`,
          borderRadius: 12,
          padding: 20,
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
          transition: 'border-color 0.15s',
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div
            style={{
              width: 40, height: 40, borderRadius: 10,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 20, background: 'var(--bg-elevated)', flexShrink: 0,
            }}
          >
            {integration.icon}
          </div>
          <div style={{ flex: 1 }}>
            <p style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>
              {integration.display_name}
            </p>
            <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              {CATEGORY_LABELS[integration.category] ?? integration.category}
            </p>
          </div>
          <ToggleSwitch
            checked={integration.is_enabled}
            onChange={handleToggle}
            disabled={toggle.isPending}
            ariaLabel={`Toggle ${integration.display_name}`}
          />
        </div>

        {/* Description */}
        <p style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.5 }}>
          {integration.description}
        </p>

        {/* Status row */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: 11, color: statusColor }}>{statusText}</span>
          <div style={{ display: 'flex', gap: 6 }}>
            {integration.last_tested && (
              <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                Tested {new Date(integration.last_tested).toLocaleDateString()}
              </span>
            )}
            <button
              className="btn btn-ghost btn-sm"
              onClick={() => setShowConfig(true)}
              style={{ fontSize: 11, padding: '2px 8px' }}
            >
              Configure
            </button>
          </div>
        </div>

        {/* Error message */}
        {integration.last_error && (
          <p style={{ fontSize: 11, color: 'var(--red)', marginTop: -4 }}>
            Error: {integration.last_error}
          </p>
        )}
      </div>

      {showConfig && (
        <IntegrationConfigModal integration={integration} onClose={() => setShowConfig(false)} />
      )}
    </>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export function IntegrationsPage({ incidentId: _incidentId }: IntegrationsPageProps) {
  const { data: integrations, isLoading } = useIntegrations()
  const [activeCategory, setActiveCategory] = useState<string>('all')

  if (isLoading) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>Loading integrations…</span>
      </div>
    )
  }

  const categories = ['all', ...Array.from(new Set((integrations ?? []).map((i) => i.category)))]

  const filtered = (integrations ?? []).filter(
    (i) => activeCategory === 'all' || i.category === activeCategory
  )

  // Group by category for display
  const grouped = filtered.reduce<Record<string, Integration[]>>((acc, i) => {
    const cat = CATEGORY_LABELS[i.category] ?? i.category
    if (!acc[cat]) acc[cat] = []
    acc[cat].push(i)
    return acc
  }, {})

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: 24 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <div>
          <h2 style={{ fontSize: 18, fontWeight: 800, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 10 }}>
            🔗 Integrations
          </h2>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 4 }}>
            Connect external tools. Enable enrichment, notifications, and report delivery.
          </p>
        </div>
      </div>

      {/* Category filter tabs */}
      <div style={{ display: 'flex', gap: 0, marginBottom: 24, overflowX: 'auto', borderBottom: '1px solid var(--border)' }}>
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            style={{
              padding: '8px 14px',
              fontSize: 12,
              fontWeight: 600,
              color: activeCategory === cat ? 'var(--accent)' : 'var(--text-muted)',
              background: 'transparent',
              border: 'none',
              borderBottom: `2px solid ${activeCategory === cat ? 'var(--accent)' : 'transparent'}`,
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              textTransform: 'capitalize',
            }}
          >
            {cat === 'all' ? 'All' : CATEGORY_LABELS[cat as keyof typeof CATEGORY_LABELS] ?? cat}
          </button>
        ))}
      </div>

      {/* Integration cards grouped by category */}
      {Object.entries(grouped).map(([category, items]) => (
        <div key={category} style={{ marginBottom: 32 }}>
          <h3 style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 12 }}>
            {category}
          </h3>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
              gap: 16,
            }}
          >
            {items.map((integration) => {
              const card = <IntegrationCard key={integration.name} integration={integration} />
              return integration.is_premium ? (
                <PremiumGate key={integration.name} featureKey={`integration_${integration.category}`}>
                  {card}
                </PremiumGate>
              ) : (
                <div key={integration.name}>{card}</div>
              )
            })}
          </div>
        </div>
      ))}

      {filtered.length === 0 && (
        <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 40, fontSize: 13 }}>
          No integrations in this category.
        </div>
      )}
    </div>
  )
}
