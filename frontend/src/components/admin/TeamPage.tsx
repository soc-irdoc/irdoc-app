import { useState } from 'react'
import {
  useOrgUsers,
  useInvites,
  useSendInvite,
  useRevokeInvite,
  useUpdateUserRole,
  useDeactivateUser,
} from '@/hooks/useAdmin'
import { useAuthStore } from '@/stores/authStore'
import { useUIStore } from '@/stores/uiStore'
import { Modal } from '@/components/common/Modal'
import { ROLE_LABELS, ROLE_COLORS } from '@/types/admin'
import type { OrgUser } from '@/types/admin'

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
        <button className="btn btn-ghost btn-sm" onClick={onClose}>
          Cancel
        </button>
        <button className="btn btn-danger btn-sm" onClick={onConfirm}>
          Deactivate
        </button>
      </div>
    </Modal>
  )
}

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
            Email
          </label>
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
            Role
          </label>
          <div className="select-wrap">
            <select
              className="form-input"
              value={role}
              onChange={(e) => setRole(e.target.value)}
            >
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
          <button
            type="submit"
            className="btn btn-accent btn-sm"
            disabled={sendInvite.isPending}
          >
            {sendInvite.isPending ? 'Sending…' : 'Send Invite'}
          </button>
        </div>
      </form>
    </Modal>
  )
}

export function TeamPage() {
  const addToast = useUIStore((s) => s.addToast)
  const currentUser = useAuthStore((s) => s.user)
  const { data: users = [], isLoading: usersLoading } = useOrgUsers()
  const { data: invites = [], isLoading: invitesLoading } = useInvites()
  const updateRole = useUpdateUserRole()
  const deactivate = useDeactivateUser()
  const revokeInvite = useRevokeInvite()
  const sendInvite = useSendInvite()

  const [showInviteModal, setShowInviteModal] = useState(false)
  const [editingRoleId, setEditingRoleId] = useState<string | null>(null)
  const [pendingRole, setPendingRole] = useState<string>('')
  const [deactivateTarget, setDeactivateTarget] = useState<OrgUser | null>(null)

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

  async function handleResend(email: string, role: string) {
    try {
      await sendInvite.mutateAsync({ email, role })
      addToast(`Invitation resent to ${email}`, 'success')
    } catch {
      addToast('Failed to resend invitation', 'error')
    }
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

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: 24 }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 24,
        }}
      >
        <h2
          style={{ fontSize: 18, fontWeight: 800, color: 'var(--text-primary)' }}
        >
          👥 Team Members
        </h2>
        <button className="btn btn-accent btn-sm" onClick={() => setShowInviteModal(true)}>
          + Invite User
        </button>
      </div>

      {/* Active Members */}
      <div
        style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border)',
          borderRadius: 12,
          overflow: 'hidden',
          marginBottom: 24,
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
          Active Members ({users.filter((u) => u.is_active).length})
        </div>

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
                        <span
                          style={{
                            marginLeft: 8,
                            fontSize: 10,
                            color: 'var(--accent)',
                            fontWeight: 600,
                          }}
                        >
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
                            className="btn btn-accent btn-sm"
                            style={{ padding: '3px 8px', fontSize: 11 }}
                            onClick={() => handleRoleSave(u.id)}
                            disabled={updateRole.isPending}
                          >
                            Save
                          </button>
                          <button
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
                    <td style={{ ...tableCellStyle, color: 'var(--text-muted)', fontSize: 12 }}>
                      {new Date(u.created_at).toLocaleDateString()}
                    </td>
                    <td style={{ ...tableCellStyle, textAlign: 'right' }}>
                      <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                        {editingRoleId !== u.id && (
                          <button
                            className="btn btn-ghost btn-sm"
                            onClick={() => {
                              setEditingRoleId(u.id)
                              setPendingRole(u.role)
                            }}
                          >
                            Edit Role
                          </button>
                        )}
                        <button
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
      </div>

      {/* Pending Invites */}
      <div
        style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border)',
          borderRadius: 12,
          overflow: 'hidden',
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
          Pending Invitations ({invites.filter((i) => !i.accepted_at).length})
        </div>

        {invitesLoading ? (
          <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
            Loading invitations…
          </div>
        ) : invites.filter((i) => !i.accepted_at).length === 0 ? (
          <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
            No pending invitations
          </div>
        ) : (
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
                {invites
                  .filter((i) => !i.accepted_at)
                  .map((invite) => (
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
                          <button
                            className="btn btn-ghost btn-sm"
                            onClick={() => handleResend(invite.email, invite.role)}
                          >
                            Resend
                          </button>
                          <button
                            className="btn btn-danger btn-sm"
                            onClick={() => handleRevoke(invite.id)}
                          >
                            Revoke
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        )}
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
    </div>
  )
}
