import { useState, useEffect } from 'react'
import { useSSOConfig, useUpdateSSOConfig } from '@/hooks/useAdmin'
import { useUIStore } from '@/stores/uiStore'
import { PremiumGate } from '@/components/common/PremiumGate'

const IDP_OPTIONS = [
  { value: 'azure_ad', label: 'Azure AD / Entra ID' },
  { value: 'okta', label: 'Okta' },
  { value: 'google', label: 'Google Workspace' },
  { value: 'generic_saml', label: 'Generic SAML 2.0' },
]

const ROLE_OPTIONS = ['viewer', 'analyst', 'senior_analyst', 'admin']

interface RoleMapping {
  group: string
  role: string
}

function SSOForm() {
  const addToast = useUIStore((s) => s.addToast)
  const { data: ssoConfig, isLoading } = useSSOConfig()
  const updateSSO = useUpdateSSOConfig()

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
    if (ssoConfig) {
      setIsEnabled(ssoConfig.is_enabled)
      setProvider(ssoConfig.provider || 'azure_ad')
      setMetadataUrl(ssoConfig.idp_metadata_url ?? '')
      setEntityId(ssoConfig.entity_id ?? '')
      setSsoUrl(ssoConfig.sso_url ?? '')
      setAttrEmail(ssoConfig.attr_email ?? 'email')
      setAttrName(ssoConfig.attr_name ?? 'displayName')
      setAttrGroups(ssoConfig.attr_groups ?? 'groups')
      const mappings = Object.entries(ssoConfig.role_mappings ?? {}).map(([group, role]) => ({
        group,
        role,
      }))
      setRoleMappings(mappings)
    }
  }, [ssoConfig])

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

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    const mappingsObj: Record<string, string> = {}
    roleMappings.forEach(({ group, role }) => {
      if (group) mappingsObj[group] = role
    })
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

  function addMapping() {
    setRoleMappings((prev) => [...prev, { group: '', role: 'analyst' }])
  }

  function updateMapping(index: number, field: 'group' | 'role', value: string) {
    setRoleMappings((prev) =>
      prev.map((m, i) => (i === index ? { ...m, [field]: value } : m))
    )
  }

  function removeMapping(index: number) {
    setRoleMappings((prev) => prev.filter((_, i) => i !== index))
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

  const fieldLabel = (text: string, required?: boolean) => (
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
      {required && <span style={{ color: 'var(--red)', marginLeft: 2 }}>*</span>}
    </label>
  )

  const sectionCard = (title: string, children: React.ReactNode) => (
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

  if (isLoading) {
    return (
      <div style={{ padding: 20, color: 'var(--text-muted)', fontSize: 13 }}>
        Loading SSO configuration…
      </div>
    )
  }

  return (
    <form onSubmit={handleSave} style={{ maxWidth: 640 }}>
      {/* Enable SSO */}
      {sectionCard(
        'SSO Status',
        <label
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            cursor: 'pointer',
          }}
        >
          <input
            type="checkbox"
            checked={isEnabled}
            onChange={(e) => setIsEnabled(e.target.checked)}
            style={{ width: 16, height: 16, accentColor: 'var(--accent)' }}
          />
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
              Enable SSO / SAML 2.0
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
              Users will see a "Sign in with SSO" option on the login page
            </div>
          </div>
        </label>
      )}

      {/* Identity Provider */}
      {sectionCard(
        'Identity Provider',
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            {fieldLabel('Provider')}
            <div className="select-wrap">
              <select
                className="form-input"
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
              >
                {IDP_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            {fieldLabel('IdP Metadata URL')}
            <div style={{ display: 'flex', gap: 8 }}>
              <input
                type="url"
                className="form-input"
                placeholder="https://login.microsoftonline.com/…/federationmetadata/…"
                value={metadataUrl}
                onChange={(e) => setMetadataUrl(e.target.value)}
              />
              <button
                type="button"
                className="btn btn-ghost"
                style={{ whiteSpace: 'nowrap' }}
                onClick={handleLoadMetadata}
                disabled={loadingMetadata || !metadataUrl}
              >
                {loadingMetadata ? 'Loading…' : 'Load Metadata'}
              </button>
            </div>
          </div>

          <div
            style={{
              padding: '12px 16px',
              background: 'var(--bg-elevated)',
              borderRadius: 8,
              fontSize: 12,
              color: 'var(--text-muted)',
            }}
          >
            Or configure manually:
          </div>

          <div>
            {fieldLabel('Entity ID (Issuer)')}
            <input
              type="text"
              className="form-input"
              placeholder="https://sts.windows.net/…"
              value={entityId}
              onChange={(e) => setEntityId(e.target.value)}
            />
          </div>

          <div>
            {fieldLabel('SSO URL (Single Sign-On Service)')}
            <input
              type="url"
              className="form-input"
              placeholder="https://login.microsoftonline.com/…/saml2"
              value={ssoUrl}
              onChange={(e) => setSsoUrl(e.target.value)}
            />
          </div>
        </div>
      )}

      {/* Attribute Mapping */}
      {sectionCard(
        'Attribute Mapping',
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>
            Map SAML assertion attributes to IRDoc user fields.
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
            <div>
              {fieldLabel('Email attribute')}
              <input
                type="text"
                className="form-input"
                value={attrEmail}
                onChange={(e) => setAttrEmail(e.target.value)}
              />
            </div>
            <div>
              {fieldLabel('Name attribute')}
              <input
                type="text"
                className="form-input"
                value={attrName}
                onChange={(e) => setAttrName(e.target.value)}
              />
            </div>
            <div>
              {fieldLabel('Groups attribute')}
              <input
                type="text"
                className="form-input"
                value={attrGroups}
                onChange={(e) => setAttrGroups(e.target.value)}
              />
            </div>
          </div>
        </div>
      )}

      {/* Role Mappings */}
      {sectionCard(
        'Role Mappings',
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>
            Map IdP groups to IRDoc roles. Unmapped users receive the Analyst role by default.
          </p>

          {roleMappings.map((mapping, i) => (
            <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <input
                type="text"
                className="form-input"
                style={{ flex: 1 }}
                placeholder="IdP Group name"
                value={mapping.group}
                onChange={(e) => updateMapping(i, 'group', e.target.value)}
              />
              <span style={{ fontSize: 12, color: 'var(--text-muted)', flexShrink: 0 }}>→</span>
              <div className="select-wrap" style={{ width: 150 }}>
                <select
                  className="form-input"
                  value={mapping.role}
                  onChange={(e) => updateMapping(i, 'role', e.target.value)}
                >
                  {ROLE_OPTIONS.map((r) => (
                    <option key={r} value={r}>
                      {r.replace('_', ' ')}
                    </option>
                  ))}
                </select>
              </div>
              <button
                type="button"
                className="icon-btn"
                style={{ color: 'var(--red)', flexShrink: 0 }}
                onClick={() => removeMapping(i)}
                aria-label="Remove mapping"
              >
                ✕
              </button>
            </div>
          ))}

          <button type="button" className="btn btn-ghost btn-sm" onClick={addMapping}>
            + Add Mapping
          </button>
        </div>
      )}

      {/* SP Metadata */}
      {sectionCard(
        'Service Provider Metadata',
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            Configure these values in your Identity Provider.
          </p>

          <div>
            {fieldLabel('SP Entity ID / Audience')}
            <div style={{ display: 'flex', gap: 8 }}>
              <input
                type="text"
                className="form-input"
                value={spEntityId}
                readOnly
                style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, opacity: 0.8 }}
              />
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                style={{ whiteSpace: 'nowrap' }}
                onClick={() => copyToClipboard(spEntityId)}
              >
                Copy
              </button>
            </div>
          </div>

          <div>
            {fieldLabel('ACS URL (Assertion Consumer Service)')}
            <div style={{ display: 'flex', gap: 8 }}>
              <input
                type="text"
                className="form-input"
                value={acsUrl}
                readOnly
                style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, opacity: 0.8 }}
              />
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                style={{ whiteSpace: 'nowrap' }}
                onClick={() => copyToClipboard(acsUrl)}
              >
                Copy
              </button>
            </div>
          </div>
        </div>
      )}

      <button type="submit" className="btn btn-accent" disabled={updateSSO.isPending}>
        {updateSSO.isPending ? 'Saving…' : 'Save SSO Configuration'}
      </button>
    </form>
  )
}

export function SSOPage() {
  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: 24 }}>
      <h2
        style={{ fontSize: 18, fontWeight: 800, color: 'var(--text-primary)', marginBottom: 24 }}
      >
        🔐 Single Sign-On (SAML 2.0)
      </h2>

      <div style={{ position: 'relative' }}>
        <PremiumGate featureKey="sso_saml">
          <SSOForm />
        </PremiumGate>
      </div>
    </div>
  )
}
