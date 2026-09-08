import { useState, useEffect } from 'react'
import { useSmtpConfig, useSaveSmtpConfig, useTestSmtp } from '@/hooks/useSmtp'
import { useOrgSettings } from '@/hooks/useAdmin'
import { useUIStore } from '@/stores/uiStore'
import { ToggleSwitch } from '@/components/common/ToggleSwitch'

const MASKED = '••••••'
const PRODUCT_ORANGE = '#f97316'

const subLabel = (text: string, optional = false) => (
  <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' as const, letterSpacing: '0.5px', marginBottom: 6, display: 'block' }}>
    {text}{optional && <span style={{ fontSize: 10, fontWeight: 400, textTransform: 'none', marginLeft: 4 }}>(optional)</span>}
  </label>
)

const subCard = (title: string, children: React.ReactNode) => (
  <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden', marginBottom: 12 }}>
    <div style={{ padding: '10px 16px', borderBottom: '1px solid var(--border)', fontSize: 12, fontWeight: 700, color: 'var(--text-secondary)' }}>{title}</div>
    <div style={{ padding: 16 }}>{children}</div>
  </div>
)

interface FormState {
  isEnabled: boolean
  host: string
  port: number
  useTls: boolean
  username: string
  password: string
  fromName: string
  fromAddress: string
  subjectTemplate: string
  logoUrl: string
  accentColor: string
  footerText: string
}

const DEFAULT_STATE: FormState = {
  isEnabled: false,
  host: '',
  port: 587,
  useTls: true,
  username: '',
  password: '',
  fromName: 'IRDoc Alerts',
  fromAddress: '',
  subjectTemplate: "You've been invited to join {org_name}",
  logoUrl: '',
  accentColor: PRODUCT_ORANGE,
  footerText: '',
}

function InvitePreview({ fromName, subjectTemplate, accentColor, logoUrl, footerText, orgName }: {
  fromName: string
  subjectTemplate: string
  accentColor: string
  logoUrl: string
  footerText: string
  orgName: string
}) {
  const subject = subjectTemplate.replace('{org_name}', orgName) || `You've been invited to join ${orgName}`
  const color = accentColor || PRODUCT_ORANGE

  return (
    <div style={{ background: '#ffffff', borderRadius: 8, padding: '18px 16px', fontFamily: 'Arial, sans-serif', fontSize: 12, color: '#222', border: '1px solid #e0e0e0', lineHeight: 1.5 }}>
      {logoUrl && (
        <div style={{ textAlign: 'center', marginBottom: 12 }}>
          <img src={logoUrl} alt="" style={{ maxHeight: 40, maxWidth: '100%' }} />
        </div>
      )}
      <div style={{ borderTop: `3px solid ${color}`, paddingTop: 14, marginBottom: 10 }}>
        <div style={{ color: '#999', fontSize: 11, marginBottom: 4 }}>From: {fromName || 'IRDoc Alerts'}</div>
        <div style={{ fontWeight: 700, fontSize: 14, color: '#1a1a2e', marginBottom: 6 }}>{subject}</div>
        <div style={{ color: '#555', marginBottom: 12 }}>
          Admin has invited you to join <strong>{orgName}</strong> on IRDoc — an Incident Response Documentation Platform.
        </div>
        <div style={{ marginBottom: 12 }}>
          <a href="#" style={{ display: 'inline-block', background: color, color: '#fff', padding: '10px 22px', borderRadius: 6, fontWeight: 700, textDecoration: 'none', fontSize: 12 }}>
            Accept Invitation
          </a>
        </div>
        <div style={{ color: '#999', fontSize: 11 }}>This link expires in 48 hours.</div>
        <div style={{ color: '#bbb', fontSize: 10, marginTop: 4 }}>If you did not expect this invitation, you can safely ignore this email.</div>
      </div>
      {footerText && (
        <div style={{ borderTop: '1px solid #eee', paddingTop: 8, color: '#aaa', fontSize: 10, textAlign: 'center' }}>{footerText}</div>
      )}
    </div>
  )
}

export function SmtpSection() {
  const addToast = useUIStore((s) => s.addToast)
  const { data: smtpConfig } = useSmtpConfig()
  const { data: orgSettings } = useOrgSettings()
  const saveConfig = useSaveSmtpConfig()
  const testSmtp = useTestSmtp()

  const [expanded, setExpanded] = useState(false)
  const [form, setForm] = useState<FormState>(DEFAULT_STATE)
  const [passwordSaved, setPasswordSaved] = useState(false)
  const [testResult, setTestResult] = useState<{ ok: boolean; error: string | null } | null>(null)

  // Seed form from DB config, falling back to org settings for logo/accent
  useEffect(() => {
    // Wait until at least orgSettings is available so defaults are accurate
    if (orgSettings === undefined) return

    const orgAccent = orgSettings?.accent_color || PRODUCT_ORANGE
    const orgLogo = orgSettings?.logo_url || ''

    if (smtpConfig) {
      setForm({
        isEnabled: smtpConfig.is_enabled,
        host: smtpConfig.host ?? '',
        port: smtpConfig.port,
        useTls: smtpConfig.use_tls,
        username: smtpConfig.username ?? '',
        password: '',
        fromName: smtpConfig.from_name ?? 'IRDoc Alerts',
        fromAddress: smtpConfig.from_address ?? '',
        subjectTemplate: smtpConfig.subject_template,
        logoUrl: smtpConfig.logo_url ?? orgLogo,
        accentColor: smtpConfig.accent_color || orgAccent,
        footerText: smtpConfig.footer_text ?? '',
      })
      setPasswordSaved(smtpConfig.password === MASKED)
    } else if (smtpConfig === null) {
      // No config yet — pre-fill branding from org settings
      setForm((prev) => ({ ...prev, logoUrl: orgLogo, accentColor: orgAccent }))
    }
  }, [smtpConfig, orgSettings])

  const set = (key: keyof FormState) => (value: FormState[typeof key]) =>
    setForm((prev) => ({ ...prev, [key]: value }))

  const isConfigured = !!smtpConfig?.host
  const statusColor = isConfigured && smtpConfig?.is_enabled ? 'var(--green)' : 'var(--text-muted)'
  const statusText = isConfigured && smtpConfig?.is_enabled
    ? `Connected to ${smtpConfig.host}`
    : isConfigured
    ? 'Configured (disabled)'
    : 'Not configured'

  const orgName = orgSettings?.name || 'Your Organization'

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    if (!form.host.trim()) {
      addToast('SMTP host is required', 'error')
      return
    }
    if (!form.fromAddress.trim()) {
      addToast('From address is required', 'error')
      return
    }
    try {
      await saveConfig.mutateAsync({
        is_enabled: form.isEnabled,
        host: form.host || undefined,
        port: form.port,
        use_tls: form.useTls,
        username: form.username || undefined,
        password: form.password || null,
        from_name: form.fromName || undefined,
        from_address: form.fromAddress || undefined,
        subject_template: form.subjectTemplate || undefined,
        logo_url: form.logoUrl || null,
        accent_color: form.accentColor || undefined,
        footer_text: form.footerText || null,
      })
      addToast('SMTP configuration saved.', 'success')
      setForm((prev) => ({ ...prev, password: '' }))
    } catch {
      addToast('Failed to save SMTP configuration.', 'error')
    }
  }

  async function handleTest() {
    setTestResult(null)
    try {
      const result = await testSmtp.mutateAsync({
        host: form.host,
        port: form.port,
        use_tls: form.useTls,
        username: form.username || null,
        password: form.password || null,
        from_name: form.fromName || null,
        from_address: form.fromAddress || null,
      })
      setTestResult(result ?? { ok: false, error: 'No response from server' })
    } catch (err: unknown) {
      setTestResult({ ok: false, error: err instanceof Error ? err.message : 'Unknown error' })
    }
  }

  return (
    <div style={{ marginBottom: 32 }} id="smtp-section">
      <h3 style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 12 }}>
        Email (SMTP)
      </h3>
      <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 14, marginTop: -8 }}>
        Configure outbound email for user invitations.
      </p>

      <div style={{
        background: 'var(--bg-surface)',
        border: `1px solid ${form.isEnabled ? 'var(--accent)' : 'var(--border)'}`,
        borderRadius: 12,
        overflow: 'hidden',
        transition: 'border-color 0.15s',
      }}>
        {/* Header */}
        <div style={{ padding: '16px 20px', display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{ width: 40, height: 40, borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-elevated)', flexShrink: 0 }}>
            <img src="/icons/envelope_color.svg" width={20} height={20} alt="" aria-hidden="true" />
          </div>
          <div style={{ flex: 1 }}>
            <p style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>SMTP Server</p>
            <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>Outbound email delivery for invites and notifications</p>
          </div>
          <ToggleSwitch
            checked={form.isEnabled}
            onChange={(v) => set('isEnabled')(v)}
            ariaLabel="Enable SMTP"
          />
        </div>

        {/* Status + expand */}
        <div style={{ padding: '0 20px 14px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: 11, color: statusColor }}>{statusText}</span>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            style={{ fontSize: 11, padding: '2px 10px' }}
            onClick={() => setExpanded((v) => !v)}
          >
            {expanded ? 'Collapse ▲' : 'Configure ▼'}
          </button>
        </div>

        {expanded && (
          <form onSubmit={handleSave}>
            <div style={{ borderTop: '1px solid var(--border)', padding: '20px 20px 0' }}>

              {/* Connection */}
              {subCard('Connection',
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 120px', gap: 10, alignItems: 'end' }}>
                    <div>
                      {subLabel('SMTP Host')}
                      <input
                        className="form-input"
                        type="text"
                        placeholder="smtp.gmail.com"
                        value={form.host}
                        onChange={(e) => set('host')(e.target.value)}
                      />
                    </div>
                    <div>
                      {subLabel('Port')}
                      <input
                        className="form-input"
                        type="number"
                        min={1}
                        max={65535}
                        value={form.port}
                        onChange={(e) => set('port')(parseInt(e.target.value, 10) || 587)}
                      />
                    </div>
                    <div>
                      {subLabel('TLS')}
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, height: 36 }}>
                        <ToggleSwitch
                          checked={form.useTls}
                          onChange={(v) => set('useTls')(v)}
                          ariaLabel="Use TLS"
                        />
                        <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{form.useTls ? 'On' : 'Off'}</span>
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                    <div>
                      {subLabel('Username')}
                      <input
                        className="form-input"
                        type="text"
                        placeholder="you@company.com"
                        value={form.username}
                        onChange={(e) => set('username')(e.target.value)}
                      />
                    </div>
                    <div>
                      {subLabel('Password')}
                      <input
                        className="form-input"
                        type="password"
                        placeholder={passwordSaved ? 'unchanged' : 'enter password'}
                        value={form.password}
                        onChange={(e) => set('password')(e.target.value)}
                      />
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      onClick={handleTest}
                      disabled={testSmtp.isPending || !form.host}
                      style={{ display: 'flex', alignItems: 'center', gap: 6 }}
                    >
                      {testSmtp.isPending ? 'Sending…' : <><img src="/icons/outbox_tray_color.svg" width={14} height={14} alt="" aria-hidden="true" style={{ verticalAlign: 'middle', marginRight: 4 }} />Send Test Email</>}
                    </button>
                    <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>sends to your account email</span>
                    {testResult && (
                      <div style={{
                        padding: '4px 10px',
                        borderRadius: 5,
                        fontSize: 11,
                        background: testResult.ok ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)',
                        color: testResult.ok ? 'var(--green)' : 'var(--red)',
                        border: `1px solid ${testResult.ok ? 'var(--green)' : 'var(--red)'}`,
                      }}>
                        {testResult.ok ? '✓ Test email sent' : `✗ ${testResult.error}`}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Email Template */}
              {subCard('Email Template',
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
                  {/* Fields */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                      <div>
                        {subLabel('Display Name')}
                        <input
                          className="form-input"
                          type="text"
                          placeholder="IRDoc Alerts"
                          value={form.fromName}
                          onChange={(e) => set('fromName')(e.target.value)}
                        />
                      </div>
                      <div>
                        {subLabel('From Address')}
                        <input
                          className="form-input"
                          type="email"
                          placeholder="noreply@company.com"
                          value={form.fromAddress}
                          onChange={(e) => set('fromAddress')(e.target.value)}
                        />
                      </div>
                    </div>

                    <div>
                      {subLabel('Subject Line')}
                      <input
                        className="form-input"
                        type="text"
                        placeholder="You've been invited to join {org_name}"
                        value={form.subjectTemplate}
                        onChange={(e) => set('subjectTemplate')(e.target.value)}
                      />
                      <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4 }}>
                        Use <code style={{ background: 'var(--bg-elevated)', padding: '1px 4px', borderRadius: 3 }}>{'{org_name}'}</code> as a placeholder
                      </div>
                    </div>

                    <div>
                      {subLabel('Logo URL', true)}
                      <input
                        className="form-input"
                        type="url"
                        placeholder={orgSettings?.logo_url || 'https://example.com/logo.png'}
                        value={form.logoUrl}
                        onChange={(e) => set('logoUrl')(e.target.value)}
                      />
                      {orgSettings?.logo_url && !form.logoUrl && (
                        <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4 }}>
                          Leave blank to use the logo from{' '}
                          <span style={{ color: 'var(--accent)' }}>Organization Settings</span>
                        </div>
                      )}
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 60px', gap: 8 }}>
                      <div>
                        {subLabel('Accent Color')}
                        <input
                          className="form-input"
                          type="text"
                          placeholder={PRODUCT_ORANGE}
                          value={form.accentColor}
                          onChange={(e) => set('accentColor')(e.target.value)}
                        />
                      </div>
                      <div>
                        {subLabel(' ')}
                        <input
                          type="color"
                          value={form.accentColor || PRODUCT_ORANGE}
                          onChange={(e) => set('accentColor')(e.target.value)}
                          style={{ width: '100%', height: 36, border: '1px solid var(--border)', borderRadius: 6, background: 'var(--bg-elevated)', cursor: 'pointer', padding: 2 }}
                        />
                      </div>
                    </div>

                    <div>
                      {subLabel('Footer Text', true)}
                      <input
                        className="form-input"
                        type="text"
                        placeholder={`© ${new Date().getFullYear()} ${orgName}. All rights reserved.`}
                        value={form.footerText}
                        onChange={(e) => set('footerText')(e.target.value)}
                      />
                    </div>
                  </div>

                  {/* Live preview */}
                  <div>
                    <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 8 }}>
                      Live Preview
                    </div>
                    <InvitePreview
                      fromName={form.fromName}
                      subjectTemplate={form.subjectTemplate}
                      accentColor={form.accentColor}
                      logoUrl={form.logoUrl}
                      footerText={form.footerText}
                      orgName={orgName}
                    />
                  </div>
                </div>
              )}

            </div>

            {/* Save bar */}
            <div style={{ padding: '14px 20px 20px', display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => setExpanded(false)}>Collapse</button>
              <button type="submit" className="btn btn-accent btn-sm" disabled={saveConfig.isPending}>
                {saveConfig.isPending ? 'Saving…' : 'Save SMTP Configuration'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
