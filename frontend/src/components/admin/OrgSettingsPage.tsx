import { useState, useEffect } from 'react'
import { useOrgSettings, useUpdateOrgSettings } from '@/hooks/useAdmin'
import { useUIStore } from '@/stores/uiStore'
import { PremiumGate } from '@/components/common/PremiumGate'

export function OrgSettingsPage() {
  const addToast = useUIStore((s) => s.addToast)
  const { data: org, isLoading } = useOrgSettings()
  const updateOrg = useUpdateOrgSettings()

  const [name, setName] = useState('')
  const [allowRegistration, setAllowRegistration] = useState(true)

  useEffect(() => {
    if (org) {
      setName(org.name)
      setAllowRegistration(org.allow_registration)
    }
  }, [org])

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    try {
      await updateOrg.mutateAsync({ name, allow_registration: allowRegistration })
      addToast('Organisation settings saved', 'success')
    } catch {
      addToast('Failed to save settings', 'error')
    }
  }

  const planColors: Record<string, string> = {
    core: 'chip-muted',
    pro: 'chip-blue',
    enterprise: 'chip-yellow',
  }

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: 24 }}>
      <h2
        style={{ fontSize: 18, fontWeight: 800, color: 'var(--text-primary)', marginBottom: 24 }}
      >
        ⚙️ Organisation Settings
      </h2>

      <form onSubmit={handleSave} style={{ maxWidth: 560 }}>
        {/* General */}
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
            General
          </div>

          {isLoading ? (
            <div style={{ padding: 20, color: 'var(--text-muted)', fontSize: 13 }}>
              Loading…
            </div>
          ) : (
            <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
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
                  Organisation Name
                </label>
                <input
                  type="text"
                  className="form-input"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
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
                    marginBottom: 8,
                    display: 'block',
                  }}
                >
                  Plan
                </label>
                <span className={`chip ${planColors[org?.plan ?? 'core'] ?? 'chip-muted'}`}>
                  {(org?.plan ?? 'core').toUpperCase()}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Registration Policy */}
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
            Registration Policy
          </div>
          <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 10 }}>
            <label
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: 10,
                cursor: 'pointer',
              }}
            >
              <input
                type="radio"
                name="reg_policy"
                checked={allowRegistration}
                onChange={() => setAllowRegistration(true)}
                style={{ marginTop: 2, accentColor: 'var(--accent)' }}
              />
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
                  Open Registration
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                  Anyone with access to the URL can create an account
                </div>
              </div>
            </label>

            <label
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: 10,
                cursor: 'pointer',
              }}
            >
              <input
                type="radio"
                name="reg_policy"
                checked={!allowRegistration}
                onChange={() => setAllowRegistration(false)}
                style={{ marginTop: 2, accentColor: 'var(--accent)' }}
              />
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
                  Invite Only
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                  New users can only join via an invitation link
                </div>
              </div>
            </label>
          </div>
        </div>

        {/* Custom Branding */}
        <div
          style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            borderRadius: 12,
            overflow: 'hidden',
            marginBottom: 24,
            position: 'relative',
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
            Custom Branding
          </div>
          <PremiumGate featureKey="custom_branding">
            <div style={{ padding: 20 }}>
              <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                Upload your logo, set custom colours, and add a branded header to all reports.
              </p>
              <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
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
                    Logo URL
                  </label>
                  <input type="url" className="form-input" placeholder="https://…" disabled />
                </div>
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
                    Accent Colour
                  </label>
                  <input type="color" className="form-input" style={{ height: 38 }} disabled />
                </div>
              </div>
            </div>
          </PremiumGate>
        </div>

        <button
          type="submit"
          className="btn btn-accent"
          disabled={updateOrg.isPending || isLoading}
        >
          {updateOrg.isPending ? 'Saving…' : 'Save Changes'}
        </button>
      </form>
    </div>
  )
}
