import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useIntegrations, useSaveIntegrationConfig, useTestIntegration, useToggleIntegration } from '@/hooks/useIntegrations'
import { useSSOConfig, useUpdateSSOConfig } from '@/hooks/useAdmin'
import { SmtpSection } from '@/components/integrations/SmtpSection'
import { AiSection } from '@/components/integrations/AiSection'
import { useUIStore } from '@/stores/uiStore'
import { ToggleSwitch } from '@/components/common/ToggleSwitch'
import { Modal } from '@/components/common/Modal'
import { CATEGORY_LABELS } from '@/types/integration'
import type { Integration } from '@/types/integration'

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
  const toggle = useToggleIntegration()
  const [values, setValues] = useState<Record<string, string>>(() => {
    const defaults: Record<string, string> = {}
    for (const [key, field] of Object.entries(integration.config_schema)) {
      // Pre-populate with saved non-password values; password fields stay blank
      defaults[key] = integration.config_values?.[key] ?? field.default ?? ''
    }
    return defaults
  })
  const [testResult, setTestResult] = useState<{ ok: boolean; error: string | null } | null>(null)

  async function handleSave() {
    const missingFields = Object.entries(integration.config_schema)
      .filter(([key, field]) => field.required && !values[key]?.trim())
      .map(([_, field]) => field.label)
    if (missingFields.length > 0) {
      addToast(`Required fields missing: ${missingFields.join(', ')}`, 'error')
      return
    }
    try {
      await saveConfig.mutateAsync({ pluginName: integration.name, config: values })
      if (!integration.is_enabled) {
        await toggle.mutateAsync({ pluginName: integration.name, enabled: true })
      }
      addToast('Configuration saved', 'success')
      onClose()
    } catch {
      addToast('Failed to save configuration', 'error')
    }
  }

  async function handleTest() {
    const missingFields = Object.entries(integration.config_schema)
      .filter(([key, field]) => field.required && !values[key]?.trim())
      .map(([_, field]) => field.label)
    if (missingFields.length > 0) {
      addToast(`Required fields missing: ${missingFields.join(', ')}`, 'error')
      return
    }
    try {
      await saveConfig.mutateAsync({ pluginName: integration.name, config: values })
    } catch {
      addToast('Failed to save configuration', 'error')
      return
    }
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
            disabled={testConn.isPending || saveConfig.isPending}
          >
            {testConn.isPending || saveConfig.isPending ? 'Testing…' : 'Test Connection'}
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

// ── Identity & Access Section (SSO / OIDC) ───────────────────────────────────

const ROLE_OPTIONS = ['viewer', 'analyst', 'senior_analyst', 'admin']

interface RoleMapping { group: string; role: string }

function IdentitySection({ autoExpand }: { autoExpand: boolean }) {
  const addToast = useUIStore((s) => s.addToast)
  const { data: ssoConfig, isLoading } = useSSOConfig()
  const updateSSO = useUpdateSSOConfig()

  const [expanded, setExpanded] = useState(autoExpand)
  const [isEnabled, setIsEnabled] = useState(false)
  const [tenantId, setTenantId] = useState('')
  const [clientId, setClientId] = useState('')
  const [clientSecret, setClientSecret] = useState('')
  const [roleMappings, setRoleMappings] = useState<RoleMapping[]>([])

  useEffect(() => {
    if (autoExpand) setExpanded(true)
  }, [autoExpand])

  useEffect(() => {
    if (ssoConfig) {
      setIsEnabled(ssoConfig.is_enabled)
      setTenantId(ssoConfig.tenant_id ?? '')
      setClientId(ssoConfig.client_id ?? '')
      // client_secret is never returned — leave blank (user re-enters to rotate)
      setRoleMappings(
        Object.entries(ssoConfig.role_mappings ?? {}).map(([group, role]) => ({ group, role }))
      )
    }
  }, [ssoConfig])

  async function handleToggleEnable(enabled: boolean) {
    setIsEnabled(enabled)
    if (!expanded) setExpanded(true)
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    if (!tenantId.trim()) {
      addToast('Directory (Tenant) ID is required', 'error')
      return
    }
    if (!clientId.trim()) {
      addToast('Application (Client) ID is required', 'error')
      return
    }
    // Client secret required on first save — afterwards it stays encrypted in the DB
    const hasExistingSecret = !!ssoConfig?.client_id  // if client_id is saved, secret was previously set
    if (!hasExistingSecret && !clientSecret.trim()) {
      addToast('Client Secret is required for the initial configuration', 'error')
      return
    }
    const mappingsObj: Record<string, string> = {}
    roleMappings.forEach(({ group, role }) => { if (group.trim()) mappingsObj[group.trim()] = role })
    const payload: Record<string, unknown> = {
      is_enabled: isEnabled,
      tenant_id: tenantId || null,
      client_id: clientId || null,
      role_mappings: mappingsObj,
    }
    if (clientSecret.trim()) payload.client_secret = clientSecret.trim()
    try {
      await updateSSO.mutateAsync(payload)
      setClientSecret('')  // clear after save — never persisted in UI
      addToast('SSO configuration saved', 'success')
    } catch {
      addToast('Failed to save SSO configuration', 'error')
    }
  }

  async function copyToClipboard(text: string) {
    try {
      await navigator.clipboard.writeText(text)
      addToast('Copied to clipboard', 'success')
    } catch {
      addToast('Failed to copy', 'error')
    }
  }

  const redirectUri = `${window.location.origin}/api/v1/auth/oidc/callback`

  const statusColor = isEnabled ? 'var(--green)' : 'var(--text-muted)'
  const statusText = isLoading
    ? 'Loading…'
    : isEnabled
    ? 'SSO Active'
    : ssoConfig?.client_id
    ? 'Configured — inactive'
    : 'Not configured'

  const subLabel = (text: string) => (
    <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' as const, letterSpacing: '0.5px', marginBottom: 6, display: 'block' }}>
      {text}
    </label>
  )

  const subCard = (title: string, children: React.ReactNode) => (
    <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden', marginBottom: 12 }}>
      <div style={{ padding: '10px 16px', borderBottom: '1px solid var(--border)', fontSize: 12, fontWeight: 700, color: 'var(--text-secondary)' }}>{title}</div>
      <div style={{ padding: 16 }}>{children}</div>
    </div>
  )

  return (
    <div style={{ marginBottom: 32 }} id="identity-section">
      <h3 style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 12 }}>
        Single Sign-On
      </h3>
      <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 14, marginTop: -8 }}>
        Connect your identity provider for SSO and automatic user provisioning.
      </p>

      <div style={{
        background: 'var(--bg-surface)',
        border: `1px solid ${isEnabled ? 'var(--accent)' : 'var(--border)'}`,
        borderRadius: 12,
        overflow: 'hidden',
        transition: 'border-color 0.15s',
      }}>
        {/* Card header */}
        <div style={{ padding: '16px 20px', display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{ width: 40, height: 40, borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20, background: 'var(--bg-elevated)', flexShrink: 0 }}>
            🔐
          </div>
          <div style={{ flex: 1 }}>
            <p style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>Single Sign-On (SSO)</p>
            <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>Entra ID / Azure AD — OAuth2 / OIDC</p>
          </div>
          <ToggleSwitch checked={isEnabled} onChange={handleToggleEnable} ariaLabel="Toggle SSO" />
        </div>

        {/* Status + configure */}
        <div style={{ padding: '0 20px 14px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: 11, color: statusColor }}>{statusText}</span>
          <button className="btn btn-ghost btn-sm" style={{ fontSize: 11, padding: '2px 10px' }} onClick={() => setExpanded((v) => !v)}>
            {expanded ? 'Collapse ▲' : 'Configure ▼'}
          </button>
        </div>

        {expanded && (
          <form onSubmit={handleSave}>
            <div style={{ borderTop: '1px solid var(--border)', padding: '20px 20px 0' }}>

              {subCard('Azure App Registration Credentials',
                <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                  <div style={{ background: 'rgba(99,102,241,0.07)', border: '1px solid rgba(99,102,241,0.2)', borderRadius: 8, padding: '10px 14px', fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                    <strong style={{ color: 'var(--text-primary)' }}>OAuth2 / OIDC — no SAML required.</strong>{' '}
                    Create an <strong>App Registration</strong> (not an Enterprise Application) in Entra ID and add the Redirect URI below.
                    The same App Registration can be shared with SharePoint sync — they are configured independently.
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                    <div>
                      {subLabel('Directory (Tenant) ID')}
                      <input
                        type="text"
                        className="form-input"
                        placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                        value={tenantId}
                        onChange={(e) => setTenantId(e.target.value)}
                      />
                      <p style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 3 }}>
                        Azure portal → Entra ID → Overview → Directory (tenant) ID
                      </p>
                    </div>
                    <div>
                      {subLabel('Application (Client) ID')}
                      <input
                        type="text"
                        className="form-input"
                        placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                        value={clientId}
                        onChange={(e) => setClientId(e.target.value)}
                      />
                      <p style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 3 }}>
                        App Registration → Overview → Application (client) ID
                      </p>
                    </div>
                  </div>

                  <div>
                    {subLabel('Client Secret')}
                    <input
                      type="password"
                      className="form-input"
                      placeholder="Paste new secret to set or rotate — leave blank to keep existing"
                      value={clientSecret}
                      onChange={(e) => setClientSecret(e.target.value)}
                      autoComplete="new-password"
                    />
                    <p style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 3 }}>
                      App Registration → Certificates &amp; secrets → Client secrets → + New client secret. Stored encrypted.
                    </p>
                  </div>
                </div>
              )}

              {subCard('Redirect URI — Register in Azure',
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                    In your App Registration → <strong>Authentication → Add a platform → Web</strong>, add this Redirect URI:
                  </p>
                  <div>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <input type="text" className="form-input" value={redirectUri} readOnly style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, opacity: 0.85 }} />
                      <button type="button" className="btn btn-ghost btn-sm" style={{ whiteSpace: 'nowrap' }} onClick={() => copyToClipboard(redirectUri)}>Copy</button>
                    </div>
                    <p style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4 }}>
                      Also ensure <strong>ID tokens</strong> is checked under Implicit grant, and the app has <strong>openid, profile, email</strong> API permissions granted.
                    </p>
                  </div>
                </div>
              )}

              {subCard('Role Mappings',
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>
                    Map Azure AD group Object IDs to IRDoc roles. Unmapped users receive the Analyst role by default.
                    To include group claims, enable <strong>Groups</strong> in your App Registration → Token configuration.
                  </p>
                  {roleMappings.map((mapping, i) => (
                    <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                      <input
                        type="text"
                        className="form-input"
                        style={{ flex: 1 }}
                        placeholder="Azure AD group Object ID (GUID)"
                        value={mapping.group}
                        onChange={(e) => setRoleMappings((prev) => prev.map((m, idx) => idx === i ? { ...m, group: e.target.value } : m))}
                      />
                      <span style={{ fontSize: 12, color: 'var(--text-muted)', flexShrink: 0 }}>→</span>
                      <div className="select-wrap" style={{ width: 150 }}>
                        <select
                          className="form-input"
                          value={mapping.role}
                          onChange={(e) => setRoleMappings((prev) => prev.map((m, idx) => idx === i ? { ...m, role: e.target.value } : m))}
                        >
                          {ROLE_OPTIONS.map((r) => <option key={r} value={r}>{r.replace('_', ' ')}</option>)}
                        </select>
                      </div>
                      <button
                        type="button"
                        className="icon-btn"
                        style={{ color: 'var(--red)', flexShrink: 0 }}
                        onClick={() => setRoleMappings((prev) => prev.filter((_, idx) => idx !== i))}
                        aria-label="Remove mapping"
                      >✕</button>
                    </div>
                  ))}
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    style={{ alignSelf: 'flex-start' }}
                    onClick={() => setRoleMappings((prev) => [...prev, { group: '', role: 'analyst' }])}
                  >
                    + Add Mapping
                  </button>
                </div>
              )}

            </div>

            <div style={{ padding: '14px 20px 20px', display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => setExpanded(false)}>Collapse</button>
              <button type="submit" className="btn btn-accent btn-sm" disabled={updateSSO.isPending}>
                {updateSSO.isPending ? 'Saving…' : 'Save SSO Configuration'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────

// Integrations hidden from UI until a future phase — backend plugins kept intact
const HIDDEN_INTEGRATIONS = new Set(['teams', 'slack', 'crowdstrike', 'proofpoint', 'sentinel', 'azuread'])

export function IntegrationsPage() {
  const { data: integrations, isLoading } = useIntegrations()
  const [activeCategory, setActiveCategory] = useState<string>('all')
  const [searchParams] = useSearchParams()
  const autoExpandIdentity = searchParams.get('section') === 'identity'

  if (isLoading) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>Loading integrations…</span>
      </div>
    )
  }

  const visible = (integrations ?? []).filter((i) => !HIDDEN_INTEGRATIONS.has(i.name))

  const categories = ['all', ...Array.from(new Set(visible.map((i) => i.category))), 'sso', 'email', 'ai']

  const filtered = visible.filter(
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
            {cat === 'all' ? 'All' : cat === 'sso' ? 'Single Sign-On' : cat === 'email' ? 'Email' : cat === 'ai' ? 'AI' : CATEGORY_LABELS[cat as keyof typeof CATEGORY_LABELS] ?? cat}
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
            {items.map((integration) => (
              <div key={integration.name}>
                <IntegrationCard integration={integration} />
              </div>
            ))}
          </div>
        </div>
      ))}

      {filtered.length === 0 && activeCategory !== 'all' && activeCategory !== 'sso' && activeCategory !== 'email' && activeCategory !== 'ai' && (
        <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 40, fontSize: 13 }}>
          No integrations in this category.
        </div>
      )}

      {(activeCategory === 'all' || activeCategory === 'sso') && (
        <IdentitySection autoExpand={autoExpandIdentity} />
      )}

      {(activeCategory === 'all' || activeCategory === 'email') && (
        <SmtpSection />
      )}

      {(activeCategory === 'all' || activeCategory === 'ai') && (
        <AiSection />
      )}
    </div>
  )
}
