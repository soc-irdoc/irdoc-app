import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  useOrgSettings,
  useUpdateOrgSettings,
  useOrgUsers,
  useInvites,
  useSendInvite,
  useRevokeInvite,
  useUpdateUserRole,
  useDeactivateUser,
  useResetUserMFA,
} from '@/hooks/useAdmin'
import { useAuthStore } from '@/stores/authStore'
import { useUIStore } from '@/stores/uiStore'
import { Modal } from '@/components/common/Modal'
import { ToggleSwitch } from '@/components/common/ToggleSwitch'
import { ROLE_LABELS, ROLE_COLORS } from '@/types/admin'
import type { OrgUser } from '@/types/admin'

// ── Invite Modal ─────────────────────────────────────────────────────────────

function InviteModal({ onClose }: { onClose: () => void }) {
  const addToast = useUIStore((s) => s.addToast)
  const sendInvite = useSendInvite()
  const [email, setEmail] = useState('')
  const [role, setRole] = useState('analyst')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    try {
      await sendInvite.mutateAsync({ email, role })
      addToast(`Invitation sent to ${email}`, 'success')
      onClose()
    } catch {
      addToast('Failed to send invitation', 'error')
    }
  }

  return (
    <Modal open onClose={onClose} title="Invite Team Member" size="sm">
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div>
          <label style={labelStyle}>Email</label>
          <input
            type="email"
            className="form-input"
            placeholder="analyst@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoFocus
          />
        </div>
        <div>
          <label style={labelStyle}>Role</label>
          <div className="select-wrap">
            <select className="form-input" value={role} onChange={(e) => setRole(e.target.value)}>
              <option value="viewer">Viewer</option>
              <option value="analyst">Analyst</option>
              <option value="senior_analyst">Senior Analyst</option>
            </select>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 4 }}>
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-accent btn-sm" disabled={sendInvite.isPending}>
            {sendInvite.isPending ? 'Sending…' : 'Send Invite'}
          </button>
        </div>
      </form>
    </Modal>
  )
}

// ── Deactivate Confirm Modal ──────────────────────────────────────────────────

function ConfirmDeactivateModal({
  user,
  onConfirm,
  onClose,
}: {
  user: OrgUser
  onConfirm: () => void
  onClose: () => void
}) {
  return (
    <Modal open onClose={onClose} title="Deactivate User" size="sm">
      <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 20 }}>
        Are you sure you want to deactivate{' '}
        <strong style={{ color: 'var(--text-primary)' }}>{user.full_name}</strong>? They will lose
        access immediately.
      </p>
      <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
        <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>
          Cancel
        </button>
        <button type="button" className="btn btn-danger btn-sm" onClick={onConfirm}>
          Deactivate
        </button>
      </div>
    </Modal>
  )
}

// ── Shared styles ─────────────────────────────────────────────────────────────

const labelStyle: React.CSSProperties = {
  fontSize: 11,
  fontWeight: 600,
  color: 'var(--text-muted)',
  textTransform: 'uppercase',
  letterSpacing: '0.5px',
  marginBottom: 6,
  display: 'block',
}

const cardStyle: React.CSSProperties = {
  background: 'var(--bg-surface)',
  border: '1px solid var(--border)',
  borderRadius: 12,
  overflow: 'hidden',
  marginBottom: 16,
}

const cardHeaderStyle: React.CSSProperties = {
  padding: '14px 20px',
  borderBottom: '1px solid var(--border)',
  fontSize: 13,
  fontWeight: 700,
  color: 'var(--text-primary)',
  display: 'flex',
  alignItems: 'center',
  gap: 10,
}

const tableHeaderStyle: React.CSSProperties = {
  padding: '10px 16px',
  fontSize: 11,
  fontWeight: 600,
  color: 'var(--text-muted)',
  textTransform: 'uppercase',
  letterSpacing: '0.5px',
  textAlign: 'left',
  borderBottom: '1px solid var(--border)',
  background: 'var(--bg-elevated)',
}

const tableCellStyle: React.CSSProperties = {
  padding: '12px 16px',
  fontSize: 13,
  color: 'var(--text-primary)',
  borderBottom: '1px solid var(--border-subtle)',
  verticalAlign: 'middle',
}

// ── Main Component ────────────────────────────────────────────────────────────

type AuthSource = 'local' | 'azure' | 'onprem'

export function OrgSettingsPage() {
  const addToast = useUIStore((s) => s.addToast)
  const navigate = useNavigate()

  // Org settings
  const { data: org, isLoading } = useOrgSettings()
  const updateOrg = useUpdateOrgSettings()
  const [name, setName] = useState('')
  const [allowRegistration, setAllowRegistration] = useState(true)
  const [logoUrl, setLogoUrl] = useState('')
  const [accentColor, setAccentColor] = useState('#6366f1')

  // Team
  const currentUser = useAuthStore((s) => s.user)
  const { data: users = [], isLoading: usersLoading } = useOrgUsers()
  const { data: invites = [], isLoading: invitesLoading } = useInvites()
  const updateRole = useUpdateUserRole()
  const deactivate = useDeactivateUser()
  const resetMFA = useResetUserMFA()
  const revokeInvite = useRevokeInvite()
  const sendInvite = useSendInvite()
  const [showInviteModal, setShowInviteModal] = useState(false)
  const [editingRoleId, setEditingRoleId] = useState<string | null>(null)
  const [pendingRole, setPendingRole] = useState('')
  const [deactivateTarget, setDeactivateTarget] = useState<OrgUser | null>(null)
  const [resetMFATarget, setResetMFATarget] = useState<OrgUser | null>(null)
  const [showMFAEnforceConfirm, setShowMFAEnforceConfirm] = useState(false)

  // User auth
  const [authSource, setAuthSource] = useState<AuthSource>('local')

  useEffect(() => {
    if (org) {
      setName(org.name)
      setAllowRegistration(org.allow_registration)
      if (org.logo_url !== undefined) setLogoUrl(org.logo_url)
      if (org.accent_color !== undefined) setAccentColor(org.accent_color)
    }
  }, [org])

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    try {
      await updateOrg.mutateAsync({ name, allow_registration: allowRegistration, logo_url: logoUrl, accent_color: accentColor })
      addToast('Organisation settings saved', 'success')
    } catch {
      addToast('Failed to save settings', 'error')
    }
  }

  async function handleRoleSave(userId: string) {
    try {
      await updateRole.mutateAsync({ id: userId, role: pendingRole })
      addToast('Role updated', 'success')
      setEditingRoleId(null)
    } catch {
      addToast('Failed to update role', 'error')
    }
  }

  async function handleDeactivate(user: OrgUser) {
    try {
      await deactivate.mutateAsync(user.id)
      addToast(`${user.full_name} deactivated`, 'success')
      setDeactivateTarget(null)
    } catch {
      addToast('Failed to deactivate user', 'error')
    }
  }

  async function handleRevoke(id: string) {
    try {
      await revokeInvite.mutateAsync(id)
      addToast('Invitation revoked', 'success')
    } catch {
      addToast('Failed to revoke invitation', 'error')
    }
  }

  async function handleResetMFA(user: OrgUser) {
    try {
      await resetMFA.mutateAsync(user.id)
      addToast(`MFA reset for ${user.full_name}`, 'success')
      setResetMFATarget(null)
    } catch {
      addToast('Failed to reset MFA', 'error')
    }
  }

  async function handleMFAToggle(value: boolean) {
    if (value) {
      setShowMFAEnforceConfirm(true)
    } else {
      try {
        await updateOrg.mutateAsync({ mfa_required: false })
        addToast('MFA requirement disabled', 'success')
      } catch {
        addToast('Failed to update MFA requirement', 'error')
      }
    }
  }

  async function handleMFAEnforceConfirm() {
    try {
      await updateOrg.mutateAsync({ mfa_required: true })
      addToast('MFA is now required for all local users', 'success')
      setShowMFAEnforceConfirm(false)
    } catch {
      addToast('Failed to enable MFA requirement', 'error')
    }
  }

  async function handleResend(email: string, role: string) {
    try {
      await sendInvite.mutateAsync({ email, role })
      addToast(`Invitation resent to ${email}`, 'success')
    } catch {
      addToast('Failed to resend invitation', 'error')
    }
  }

  const planColors: Record<string, string> = {
    core: 'chip-muted',
    pro: 'chip-blue',
    enterprise: 'chip-yellow',
  }

  const AUTH_OPTIONS: { id: AuthSource; icon: string; label: string; desc: string }[] = [
    { id: 'local',  icon: 'key_color.svg', label: 'Local Users',        desc: 'Managed manually in the Team section' },
    { id: 'azure',  icon: 'cloud_color.svg', label: 'Entra ID / Azure AD', desc: 'Import users from Azure Active Directory' },
    { id: 'onprem', icon: 'office_building_color.svg', label: 'On-Premises AD',      desc: 'Sync with on-premises Active Directory' },
  ]

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: 24 }}>
      <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'Syne, sans-serif', marginBottom: 24 }}>
        Organisation Settings
      </div>

      <div style={{ maxWidth: 1020 }}>

        {/* ── General ── */}
        <div style={cardStyle}>
          <div style={cardHeaderStyle}>General</div>
          {isLoading ? (
            <div style={{ padding: 20, color: 'var(--text-muted)', fontSize: 13 }}>Loading…</div>
          ) : (
            <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div>
                <label style={labelStyle}>Organisation Name</label>
                <input
                  type="text"
                  className="form-input"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>
              <div>
                <label style={labelStyle}>Plan</label>
                <span className={`chip ${planColors[org?.plan ?? 'core'] ?? 'chip-muted'}`}>
                  {(org?.plan ?? 'core').toUpperCase()}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* ── Team Members ── */}
        <div style={cardStyle}>
          <div style={cardHeaderStyle}>
            <span style={{ flex: 1 }}>
              Team Members
              <span style={{ marginLeft: 8, fontSize: 11, fontWeight: 500, color: 'var(--text-muted)' }}>
                ({users.filter((u) => u.is_active).length} active)
              </span>
            </span>
            <button
              type="button"
              className="btn btn-accent btn-sm"
              onClick={() => setShowInviteModal(true)}
            >
              + Invite User
            </button>
          </div>

          {/* Active members */}
          {usersLoading ? (
            <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
              Loading members…
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    <th style={tableHeaderStyle}>Name</th>
                    <th style={tableHeaderStyle}>Email</th>
                    <th style={tableHeaderStyle}>Role</th>
                    <th style={tableHeaderStyle}>Status</th>
                    <th style={tableHeaderStyle}>2FA</th>
                    <th style={tableHeaderStyle}>Joined</th>
                    <th style={{ ...tableHeaderStyle, textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id}>
                      <td style={tableCellStyle}>
                        <span style={{ fontWeight: 600 }}>{u.full_name}</span>
                        {u.id === currentUser?.id && (
                          <span style={{ marginLeft: 8, fontSize: 10, color: 'var(--accent)', fontWeight: 600 }}>
                            (you)
                          </span>
                        )}
                      </td>
                      <td style={{ ...tableCellStyle, color: 'var(--text-muted)', fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }}>
                        {u.email}
                      </td>
                      <td style={tableCellStyle}>
                        {editingRoleId === u.id ? (
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            <div className="select-wrap" style={{ minWidth: 140 }}>
                              <select
                                className="form-input"
                                style={{ padding: '4px 28px 4px 8px', fontSize: 12 }}
                                value={pendingRole}
                                onChange={(e) => setPendingRole(e.target.value)}
                              >
                                <option value="viewer">Viewer</option>
                                <option value="analyst">Analyst</option>
                                <option value="senior_analyst">Senior Analyst</option>
                                <option value="admin">Admin</option>
                              </select>
                            </div>
                            <button
                              type="button"
                              className="btn btn-accent btn-sm"
                              style={{ padding: '3px 8px', fontSize: 11 }}
                              onClick={() => handleRoleSave(u.id)}
                              disabled={updateRole.isPending}
                            >
                              Save
                            </button>
                            <button
                              type="button"
                              className="btn btn-ghost btn-sm"
                              style={{ padding: '3px 8px', fontSize: 11 }}
                              onClick={() => setEditingRoleId(null)}
                            >
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <span className={`chip ${ROLE_COLORS[u.role] ?? 'chip-muted'}`}>
                            {ROLE_LABELS[u.role] ?? u.role}
                          </span>
                        )}
                      </td>
                      <td style={tableCellStyle}>
                        <span className={`chip ${u.is_active ? 'chip-green' : 'chip-muted'}`}>
                          {u.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td style={tableCellStyle}>
                        {u.auth_provider === 'oidc' ? (
                          <span className="chip chip-blue" title="MFA is managed by the identity provider">Via SSO</span>
                        ) : u.mfa_enabled ? (
                          <span className="chip chip-green">Enabled</span>
                        ) : org?.mfa_required ? (
                          <span className="chip chip-yellow">Not set</span>
                        ) : (
                          <span className="chip chip-muted">Off</span>
                        )}
                      </td>
                      <td style={{ ...tableCellStyle, color: 'var(--text-muted)', fontSize: 12 }}>
                        {new Date(u.created_at).toLocaleDateString()}
                      </td>
                      <td style={{ ...tableCellStyle, textAlign: 'right' }}>
                        <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                          {editingRoleId !== u.id && (
                            <button
                              type="button"
                              className="btn btn-ghost btn-sm"
                              onClick={() => { setEditingRoleId(u.id); setPendingRole(u.role) }}
                            >
                              Edit Role
                            </button>
                          )}
                          {u.mfa_enabled && u.auth_provider !== 'oidc' && (
                            <button
                              type="button"
                              className="btn btn-ghost btn-sm"
                              style={{ color: 'var(--yellow)' }}
                              onClick={() => setResetMFATarget(u)}
                              title="Reset MFA — user must re-enroll on next login"
                            >
                              Reset MFA
                            </button>
                          )}
                          <button
                            type="button"
                            className="btn btn-danger btn-sm"
                            disabled={u.id === currentUser?.id || !u.is_active}
                            onClick={() => setDeactivateTarget(u)}
                            title={u.id === currentUser?.id ? 'Cannot deactivate yourself' : ''}
                          >
                            Deactivate
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pending invites */}
          {!invitesLoading && invites.filter((i) => !i.accepted_at).length > 0 && (
            <>
              <div style={{
                padding: '10px 20px',
                borderTop: '1px solid var(--border)',
                fontSize: 12,
                fontWeight: 700,
                color: 'var(--text-muted)',
                background: 'var(--bg-elevated)',
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
              }}>
                Pending Invitations ({invites.filter((i) => !i.accepted_at).length})
              </div>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr>
                      <th style={tableHeaderStyle}>Email</th>
                      <th style={tableHeaderStyle}>Role</th>
                      <th style={tableHeaderStyle}>Expires</th>
                      <th style={{ ...tableHeaderStyle, textAlign: 'right' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {invites.filter((i) => !i.accepted_at).map((invite) => (
                      <tr key={invite.id}>
                        <td style={{ ...tableCellStyle, fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }}>
                          {invite.email}
                        </td>
                        <td style={tableCellStyle}>
                          <span className={`chip ${ROLE_COLORS[invite.role] ?? 'chip-muted'}`}>
                            {ROLE_LABELS[invite.role] ?? invite.role}
                          </span>
                        </td>
                        <td style={{ ...tableCellStyle, color: 'var(--text-muted)', fontSize: 12 }}>
                          {new Date(invite.expires_at).toLocaleDateString()}
                        </td>
                        <td style={{ ...tableCellStyle, textAlign: 'right' }}>
                          <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                            <button type="button" className="btn btn-ghost btn-sm" onClick={() => handleResend(invite.email, invite.role)}>
                              Resend
                            </button>
                            <button type="button" className="btn btn-danger btn-sm" onClick={() => handleRevoke(invite.id)}>
                              Revoke
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>

        {/* ── User Authentication ── */}
        <div style={cardStyle}>
          <div style={cardHeaderStyle}>User Authentication</div>
          <div style={{ padding: 20 }}>

            {/* Radio cards */}
            <div style={{ display: 'flex', gap: 10, marginBottom: 16, flexWrap: 'wrap' }}>
              {AUTH_OPTIONS.map((opt) => {
                const isSelected = authSource === opt.id
                return (
                  <label
                    key={opt.id}
                    style={{ flex: 1, minWidth: 180, cursor: 'pointer' }}
                  >
                    <div
                      onClick={() => setAuthSource(opt.id)}
                      style={{
                        padding: 14,
                        display: 'flex',
                        gap: 10,
                        alignItems: 'flex-start',
                        cursor: 'pointer',
                        transition: 'border-color 0.15s',
                        background: 'var(--bg-card)',
                        border: `1px solid ${isSelected ? 'var(--accent)' : 'var(--border)'}`,
                        borderRadius: 10,
                      }}
                    >
                      <input
                        type="radio"
                        name="auth-source"
                        value={opt.id}
                        checked={isSelected}
                        onChange={() => setAuthSource(opt.id)}
                        style={{ marginTop: 3, accentColor: 'var(--accent)', cursor: 'pointer' }}
                      />
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 6 }}>
                          <img src={`/icons/${opt.icon}`} width={18} height={18} alt="" aria-hidden="true" />
                          <span>{opt.label}</span>
                        </div>
                        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>{opt.desc}</div>
                      </div>
                    </div>
                  </label>
                )
              })}
            </div>

            {/* Local panel */}
            {authSource === 'local' && (
              <div>
                <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12 }}>
                  Local user accounts are managed in the Team section above. A permanent local admin
                  account is always retained as a break-glass account.
                </p>
                <div style={{
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border)',
                  borderRadius: 10,
                  overflow: 'hidden',
                }}>
                  <div style={{
                    padding: '8px 16px',
                    borderBottom: '1px solid var(--border)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                  }}>
                    <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)' }}>
                      Break-Glass Admin
                    </span>
                    <span className="chip chip-red" style={{ fontSize: 10 }}>Always active</span>
                  </div>
                  <div style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 12 }}>
                    <div style={{
                      width: 32,
                      height: 32,
                      borderRadius: '50%',
                      background: 'linear-gradient(135deg, var(--accent), var(--purple))',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: 11,
                      fontWeight: 800,
                      color: '#fff',
                      flexShrink: 0,
                    }}>
                      LA
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>local.admin</div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Emergency access account · Not tied to SSO</div>
                    </div>
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      onClick={() => addToast('Break-glass password rotation requires CLI access', 'info')}
                    >
                      Rotate Password
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Azure panel */}
            {authSource === 'azure' && (
              <div style={{
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border)',
                borderRadius: 10,
                padding: '14px 16px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: 12,
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--yellow, #facc15)', flexShrink: 0 }} />
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>Entra ID / Azure AD</div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 1 }}>
                      Not configured — set up SSO (OIDC) in Integrations
                    </div>
                  </div>
                </div>
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  style={{ whiteSpace: 'nowrap', flexShrink: 0 }}
                  onClick={() => navigate('/admin/integrations?section=identity')}
                >
                  Configure SSO →
                </button>
              </div>
            )}

            {/* On-premises panel */}
            {authSource === 'onprem' && (
              <div style={{
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border)',
                borderRadius: 10,
                padding: '14px 16px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: 12,
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--yellow, #facc15)', flexShrink: 0 }} />
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>On-Premises AD / LDAP</div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 1 }}>
                      Configure identity provider in Integrations
                    </div>
                  </div>
                </div>
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  style={{ whiteSpace: 'nowrap', flexShrink: 0 }}
                  onClick={() => navigate('/admin/integrations?section=identity')}
                >
                  Configure SSO →
                </button>
              </div>
            )}

            {/* MFA requirement toggle */}
            <div style={{ borderTop: '1px solid var(--border)', marginTop: 16, paddingTop: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>Require MFA for all local users</div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                  SSO users are unaffected — MFA for SSO is managed by your identity provider.
                </div>
              </div>
              <ToggleSwitch
                checked={org?.mfa_required ?? false}
                onChange={handleMFAToggle}
                ariaLabel="Require MFA for all local users"
              />
            </div>

          </div>
        </div>

        {/* ── Registration Policy + Custom Branding + Save ── */}
        <form onSubmit={handleSave}>
          {/* Registration Policy */}
          <div style={cardStyle}>
            <div style={cardHeaderStyle}>Registration Policy</div>
            <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 10 }}>
              <label style={{ display: 'flex', alignItems: 'flex-start', gap: 10, cursor: 'pointer' }}>
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
              <label style={{ display: 'flex', alignItems: 'flex-start', gap: 10, cursor: 'pointer' }}>
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
          <div style={{ ...cardStyle, marginBottom: 24 }}>
            <div style={cardHeaderStyle}>Custom Branding</div>
            <div style={{ padding: 20 }}>
              <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                Upload your logo, set custom colours, and add a branded header to all reports.
              </p>
              <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div>
                  <label style={labelStyle}>Logo URL</label>
                  <input
                    type="url"
                    className="form-input"
                    placeholder="https://…"
                    value={logoUrl}
                    onChange={(e) => setLogoUrl(e.target.value)}
                  />
                </div>
                <div>
                  <label style={labelStyle}>Accent Colour</label>
                  <input
                    type="color"
                    className="form-input"
                    style={{ height: 38 }}
                    value={accentColor}
                    onChange={(e) => setAccentColor(e.target.value)}
                  />
                </div>
              </div>
            </div>
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

      {/* Modals */}
      {showInviteModal && <InviteModal onClose={() => setShowInviteModal(false)} />}
      {deactivateTarget && (
        <ConfirmDeactivateModal
          user={deactivateTarget}
          onConfirm={() => handleDeactivate(deactivateTarget)}
          onClose={() => setDeactivateTarget(null)}
        />
      )}

      {/* MFA enforce confirmation */}
      {showMFAEnforceConfirm && (
        <Modal open onClose={() => setShowMFAEnforceConfirm(false)} title="Require MFA for all local users?" size="sm">
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 20 }}>
            Users without MFA will be required to enrol on their next login. There is no grace period.
            SSO users are not affected.
          </p>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => setShowMFAEnforceConfirm(false)}>
              Cancel
            </button>
            <button type="button" className="btn btn-accent btn-sm" onClick={handleMFAEnforceConfirm} disabled={updateOrg.isPending}>
              {updateOrg.isPending ? 'Saving…' : 'Enable'}
            </button>
          </div>
        </Modal>
      )}

      {/* MFA reset confirmation */}
      {resetMFATarget && (
        <Modal open onClose={() => setResetMFATarget(null)} title="Reset MFA for this user?" size="sm">
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 20 }}>
            <strong style={{ color: 'var(--text-primary)' }}>{resetMFATarget.full_name}</strong> will
            be required to re-enrol MFA on their next login.
          </p>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => setResetMFATarget(null)}>
              Cancel
            </button>
            <button
              type="button"
              className="btn btn-accent btn-sm"
              onClick={() => handleResetMFA(resetMFATarget)}
              disabled={resetMFA.isPending}
            >
              {resetMFA.isPending ? 'Resetting…' : 'Reset MFA'}
            </button>
          </div>
        </Modal>
      )}
    </div>
  )
}
