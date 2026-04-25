import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useIntegrations, useSaveIntegrationConfig, useTestIntegration, useToggleIntegration } from '@/hooks/useIntegrations'
import { useSSOConfig, useUpdateSSOConfig } from '@/hooks/useAdmin'
import { useUIStore } from '@/stores/uiStore'
import { ToggleSwitch } from '@/components/common/ToggleSwitch'
import PremiumGate from '@/components/common/PremiumGate'
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

// ── Identity & Access Section (SSO / SAML 2.0) ───────────────────────────────

const IDP_OPTIONS = [
  { value: 'azure_ad', label: 'Entra ID / Azure AD' },
  { value: 'okta', label: 'Okta' },
  { value: 'google', label: 'Google Workspace' },
  { value: 'generic_saml', label: 'Generic SAML 2.0' },
]

const ROLE_OPTIONS = ['viewer', 'analyst', 'senior_analyst', 'admin']

interface IdpConfig {
  metadataUrlPlaceholder: string
  entityIdPlaceholder: string
  ssoUrlPlaceholder: string
  defaultAttrEmail: string
  defaultAttrName: string
  defaultAttrGroups: string
}

const IDP_CONFIGS: Record<string, IdpConfig> = {
  azure_ad: {
    metadataUrlPlaceholder: 'https://login.microsoftonline.com/{tenant-id}/federationmetadata/2007-06/federationmetadata.xml',
    entityIdPlaceholder: 'https://sts.windows.net/{tenant-id}/',
    ssoUrlPlaceholder: 'https://login.microsoftonline.com/{tenant-id}/saml2',
    defaultAttrEmail: 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress',
    defaultAttrName: 'displayName',
    defaultAttrGroups: 'http://schemas.microsoft.com/ws/2008/06/identity/claims/groups',
  },
  okta: {
    metadataUrlPlaceholder: 'https://{subdomain}.okta.com/app/{app-id}/sso/saml/metadata',
    entityIdPlaceholder: 'http://www.okta.com/{app-id}',
    ssoUrlPlaceholder: 'https://{subdomain}.okta.com/app/{app-id}/sso/saml',
    defaultAttrEmail: 'email',
    defaultAttrName: 'displayName',
    defaultAttrGroups: 'groups',
  },
  google: {
    metadataUrlPlaceholder: 'https://accounts.google.com/o/saml2?idpid={idp-entity-id}',
    entityIdPlaceholder: 'https://accounts.google.com/o/saml2?idpid={idp-entity-id}',
    ssoUrlPlaceholder: 'https://accounts.google.com/o/saml2/idp?idpid={idp-entity-id}',
    defaultAttrEmail: 'email',
    defaultAttrName: 'displayName',
    defaultAttrGroups: 'groups',
  },
  generic_saml: {
    metadataUrlPlaceholder: 'https://your-idp.example.com/saml/metadata',
    entityIdPlaceholder: 'https://your-idp.example.com/',
    ssoUrlPlaceholder: 'https://your-idp.example.com/sso/saml',
    defaultAttrEmail: 'email',
    defaultAttrName: 'displayName',
    defaultAttrGroups: 'groups',
  },
}

interface RoleMapping { group: string; role: string }

function IdentitySection({ autoExpand }: { autoExpand: boolean }) {
  const addToast = useUIStore((s) => s.addToast)
  const { data: ssoConfig, isLoading } = useSSOConfig()
  const updateSSO = useUpdateSSOConfig()

  const [expanded, setExpanded] = useState(autoExpand)
  const [isEnabled, setIsEnabled] = useState(false)
  const [provider, setProvider] = useState('azure_ad')
  const [metadataUrl, setMetadataUrl] = useState('')
  const [entityId, setEntityId] = useState('')
  const [ssoUrl, setSsoUrl] = useState('')
  const [attrEmail, setAttrEmail] = useState('email')
  const [attrName, setAttrName] = useState('displayName')
  const [attrGroups, setAttrGroups] = useState('groups')
  const [roleMappings, setRoleMappings] = useState<RoleMapping[]>([])
  const [loadingMetadata, setLoadingMetadata] = useState(false)

  useEffect(() => {
    if (autoExpand) setExpanded(true)
  }, [autoExpand])

  useEffect(() => {
    if (ssoConfig) {
      setIsEnabled(ssoConfig.is_enabled)
      setProvider(ssoConfig.provider || 'azure_ad')
      setMetadataUrl(ssoConfig.idp_metadata_url ?? '')
      setEntityId(ssoConfig.entity_id ?? '')
      setSsoUrl(ssoConfig.sso_url ?? '')
      setAttrEmail(ssoConfig.attr_email ?? 'email')
      setAttrName(ssoConfig.attr_name ?? 'displayName')
      setAttrGroups(ssoConfig.attr_groups ?? 'groups')
      setRoleMappings(
        Object.entries(ssoConfig.role_mappings ?? {}).map(([group, role]) => ({ group, role }))
      )
    }
  }, [ssoConfig])

  function handleProviderChange(newProvider: string) {
    const oldConfig = IDP_CONFIGS[provider]
    const newConfig = IDP_CONFIGS[newProvider] ?? IDP_CONFIGS.generic_saml
    // Only update attribute names if they still match the previous provider's defaults
    // (i.e., the user hasn't customised them yet)
    if (attrEmail === oldConfig?.defaultAttrEmail) setAttrEmail(newConfig.defaultAttrEmail)
    if (attrName === oldConfig?.defaultAttrName) setAttrName(newConfig.defaultAttrName)
    if (attrGroups === oldConfig?.defaultAttrGroups) setAttrGroups(newConfig.defaultAttrGroups)
    setProvider(newProvider)
  }

  async function handleLoadMetadata() {
    if (!metadataUrl) return
    setLoadingMetadata(true)
    try {
      await updateSSO.mutateAsync({ idp_metadata_url: metadataUrl })
      addToast('Metadata loaded', 'success')
    } catch {
      addToast('Failed to load metadata', 'error')
    } finally {
      setLoadingMetadata(false)
    }
  }

  async function handleToggleEnable(enabled: boolean) {
    setIsEnabled(enabled)
    if (!expanded) setExpanded(true)
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    const mappingsObj: Record<string, string> = {}
    roleMappings.forEach(({ group, role }) => { if (group) mappingsObj[group] = role })
    try {
      await updateSSO.mutateAsync({
        is_enabled: isEnabled,
        provider,
        idp_metadata_url: metadataUrl || null,
        entity_id: entityId || null,
        sso_url: ssoUrl || null,
        attr_email: attrEmail,
        attr_name: attrName,
        attr_groups: attrGroups,
        role_mappings: mappingsObj,
      })
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

  const baseUrl = window.location.origin
  const spEntityId = `${baseUrl}/api/v1/auth/saml/metadata`
  const acsUrl = `${baseUrl}/api/v1/auth/saml/acs`

  const idpConfig = IDP_CONFIGS[provider] ?? IDP_CONFIGS.generic_saml

  const statusColor = isEnabled ? 'var(--green)' : 'var(--text-muted)'
  const statusText = isLoading
    ? 'Loading…'
    : isEnabled
    ? 'SSO Active'
    : ssoConfig?.entity_id || ssoConfig?.idp_metadata_url
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
      {/* Section heading */}
      <h3 style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 12 }}>
        Identity &amp; Access
      </h3>
      <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 14, marginTop: -8 }}>
        Connect your identity provider for SSO and user provisioning.
      </p>

      {/* SSO card */}
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
            <p style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>SSO / SAML 2.0</p>
            <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              Single Sign-On for Entra ID, Okta, Google Workspace, or any SAML 2.0 provider
            </p>
          </div>
          <ToggleSwitch
            checked={isEnabled}
            onChange={handleToggleEnable}
            ariaLabel="Toggle SSO"
          />
        </div>

        {/* Status + configure button */}
        <div style={{ padding: '0 20px 14px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: 11, color: statusColor }}>{statusText}</span>
          <button
            className="btn btn-ghost btn-sm"
            style={{ fontSize: 11, padding: '2px 10px' }}
            onClick={() => setExpanded((v) => !v)}
          >
            {expanded ? 'Collapse ▲' : 'Configure ▼'}
          </button>
        </div>

        {/* Expanded config form */}
        {expanded && (
          <form onSubmit={handleSave}>
            <div style={{ borderTop: '1px solid var(--border)', padding: '20px 20px 0' }}>

              {/* Identity Provider */}
              {subCard('Identity Provider',
                <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                  <div>
                    {subLabel('Provider')}
                    <div className="select-wrap">
                      <select className="form-input" value={provider} onChange={(e) => handleProviderChange(e.target.value)}>
                        {IDP_OPTIONS.map((opt) => (
                          <option key={opt.value} value={opt.value}>{opt.label}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <div>
                    {subLabel('IdP Metadata URL')}
                    <div style={{ display: 'flex', gap: 8 }}>
                      <input type="url" className="form-input" placeholder={idpConfig.metadataUrlPlaceholder} value={metadataUrl} onChange={(e) => setMetadataUrl(e.target.value)} />
                      <button type="button" className="btn btn-ghost btn-sm" style={{ whiteSpace: 'nowrap' }} onClick={handleLoadMetadata} disabled={loadingMetadata || !metadataUrl}>
                        {loadingMetadata ? 'Loading…' : 'Load Metadata'}
                      </button>
                    </div>
                  </div>
                  <div style={{ padding: '10px 14px', background: 'var(--bg-card)', borderRadius: 8, fontSize: 12, color: 'var(--text-muted)' }}>
                    Or configure manually:
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                    <div>
                      {subLabel('Entity ID (Issuer)')}
                      <input type="text" className="form-input" placeholder={idpConfig.entityIdPlaceholder} value={entityId} onChange={(e) => setEntityId(e.target.value)} />
                    </div>
                    <div>
                      {subLabel('SSO URL')}
                      <input type="url" className="form-input" placeholder={idpConfig.ssoUrlPlaceholder} value={ssoUrl} onChange={(e) => setSsoUrl(e.target.value)} />
                    </div>
                  </div>
                </div>
              )}

              {/* Attribute Mapping */}
              {subCard('Attribute Mapping',
                <div>
                  <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12 }}>Map SAML assertion attributes to IRDoc user fields.</p>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
                    <div>{subLabel('Email attribute')}<input type="text" className="form-input" value={attrEmail} onChange={(e) => setAttrEmail(e.target.value)} /></div>
                    <div>{subLabel('Name attribute')}<input type="text" className="form-input" value={attrName} onChange={(e) => setAttrName(e.target.value)} /></div>
                    <div>{subLabel('Groups attribute')}<input type="text" className="form-input" value={attrGroups} onChange={(e) => setAttrGroups(e.target.value)} /></div>
                  </div>
                </div>
              )}

              {/* Role Mappings */}
              {subCard('Role Mappings',
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>Map IdP groups to IRDoc roles. Unmapped users receive the Analyst role by default.</p>
                  {roleMappings.map((mapping, i) => (
                    <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                      <input type="text" className="form-input" style={{ flex: 1 }} placeholder="IdP Group name" value={mapping.group} onChange={(e) => setRoleMappings((prev) => prev.map((m, idx) => idx === i ? { ...m, group: e.target.value } : m))} />
                      <span style={{ fontSize: 12, color: 'var(--text-muted)', flexShrink: 0 }}>→</span>
                      <div className="select-wrap" style={{ width: 150 }}>
                        <select className="form-input" value={mapping.role} onChange={(e) => setRoleMappings((prev) => prev.map((m, idx) => idx === i ? { ...m, role: e.target.value } : m))}>
                          {ROLE_OPTIONS.map((r) => <option key={r} value={r}>{r.replace('_', ' ')}</option>)}
                        </select>
                      </div>
                      <button type="button" className="icon-btn" style={{ color: 'var(--red)', flexShrink: 0 }} onClick={() => setRoleMappings((prev) => prev.filter((_, idx) => idx !== i))} aria-label="Remove mapping">✕</button>
                    </div>
                  ))}
                  <button type="button" className="btn btn-ghost btn-sm" style={{ alignSelf: 'flex-start' }} onClick={() => setRoleMappings((prev) => [...prev, { group: '', role: 'analyst' }])}>
                    + Add Mapping
                  </button>
                </div>
              )}

              {/* SP Metadata */}
              {subCard('Service Provider Metadata',
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>Configure these values in your Identity Provider.</p>
                  <div>
                    {subLabel('SP Entity ID / Audience')}
                    <div style={{ display: 'flex', gap: 8 }}>
                      <input type="text" className="form-input" value={spEntityId} readOnly style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, opacity: 0.8 }} />
                      <button type="button" className="btn btn-ghost btn-sm" style={{ whiteSpace: 'nowrap' }} onClick={() => copyToClipboard(spEntityId)}>Copy</button>
                    </div>
                  </div>
                  <div>
                    {subLabel('ACS URL (Assertion Consumer Service)')}
                    <div style={{ display: 'flex', gap: 8 }}>
                      <input type="text" className="form-input" value={acsUrl} readOnly style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, opacity: 0.8 }} />
                      <button type="button" className="btn btn-ghost btn-sm" style={{ whiteSpace: 'nowrap' }} onClick={() => copyToClipboard(acsUrl)}>Copy</button>
                    </div>
                  </div>
                </div>
              )}

            </div>

            {/* Save bar */}
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
                <PremiumGate key={integration.name} featureKey="advanced_integrations">
                  {card}
                </PremiumGate>
              ) : (
                <div key={integration.name}>{card}</div>
              )
            })}
          </div>
        </div>
      ))}

      {filtered.length === 0 && activeCategory !== 'all' && (
        <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 40, fontSize: 13 }}>
          No integrations in this category.
        </div>
      )}

      {/* Identity & Access — always shown (not filtered by category) */}
      {(activeCategory === 'all' || activeCategory === 'identity') && (
        <IdentitySection autoExpand={autoExpandIdentity} />
      )}
    </div>
  )
}
