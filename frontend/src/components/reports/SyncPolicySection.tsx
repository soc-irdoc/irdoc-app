import { useState } from 'react'
import PremiumGate from '@/components/common/PremiumGate'
import { Modal } from '@/components/common/Modal'
import {
  useSyncPolicies,
  useCreateSyncPolicy,
  useDeleteSyncPolicy,
  useTriggerSyncPolicy,
  useUpdateSyncPolicy,
} from '@/hooks/useSyncPolicies'
import { useReportTemplates } from '@/hooks/useReportTemplates'
import { SyncPolicyCreate } from '@/types/report'
import { formatRelative } from '@/lib/utils'

interface Props {
  incidentId: string
}

const DEFAULT_FORM: SyncPolicyCreate = {
  destination: 'sharepoint',
  report_template_id: null,
  trigger_type: 'on_change',
  debounce_seconds: 60,
  destination_config: {},
}

export default function SyncPolicySection({ incidentId }: Props) {
  const { data: policies = [], isLoading } = useSyncPolicies(incidentId)
  const { data: templates = [] } = useReportTemplates()
  const createPolicy = useCreateSyncPolicy(incidentId)
  const deletePolicy = useDeleteSyncPolicy(incidentId)
  const triggerPolicy = useTriggerSyncPolicy(incidentId)
  const updatePolicy = useUpdateSyncPolicy(incidentId)

  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState<SyncPolicyCreate>(DEFAULT_FORM)

  const handleAdd = async () => {
    await createPolicy.mutateAsync(form)
    setShowAdd(false)
    setForm(DEFAULT_FORM)
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <h3 style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          Auto-Sync Policies
        </h3>
        <PremiumGate featureKey="sharepoint_sync">
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => setShowAdd(true)}
          >
            + Add Policy
          </button>
        </PremiumGate>
      </div>

      {isLoading ? (
        <div style={{ color: 'var(--text-muted)', fontSize: '13px' }}>Loading…</div>
      ) : policies.length === 0 ? (
        <div style={{ color: 'var(--text-muted)', fontSize: '13px', fontStyle: 'italic' }}>
          No sync policies configured.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {policies.map((p) => (
            <div
              key={p.id}
              style={{
                background: 'var(--bg-surface)',
                border: '1px solid var(--border)',
                borderRadius: '8px',
                padding: '14px 16px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                    <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 6 }}>
                      <img src="/icons/outbox_tray_color.svg" width={14} height={14} alt="" aria-hidden="true" />{p.destination.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                    </span>
                    <span
                      className={`chip ${p.is_active ? 'chip-green' : 'chip-muted'}`}
                      style={{ fontSize: '11px' }}
                    >
                      {p.is_active ? 'Active' : 'Disabled'}
                    </span>
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.6 }}>
                    <div>
                      Template: {templates.find((t) => t.id === p.report_template_id)?.name ?? 'None'}
                    </div>
                    <div>
                      Trigger: On change ({p.debounce_seconds}s debounce)
                    </div>
                    {p.last_synced_at && (
                      <div>
                        Last synced: {formatRelative(p.last_synced_at)}{' '}
                        <span className={`chip ${p.last_sync_status === 'success' ? 'chip-green' : 'chip-red'}`} style={{ fontSize: '10px' }}>
                          {p.last_sync_status}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '6px', flexShrink: 0 }}>
                  <button
                    className="btn btn-ghost btn-sm"
                    onClick={() => triggerPolicy.mutate(p.id)}
                    disabled={triggerPolicy.isPending}
                    title="Sync now"
                  >
                    ↺ Sync
                  </button>
                  <button
                    className="btn btn-ghost btn-sm"
                    onClick={() => updatePolicy.mutate({ policyId: p.id, data: { is_active: !p.is_active } })}
                  >
                    {p.is_active ? 'Disable' : 'Enable'}
                  </button>
                  <button
                    className="btn btn-danger btn-sm"
                    onClick={() => {
                      if (confirm('Delete this sync policy?')) deletePolicy.mutate(p.id)
                    }}
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {showAdd && (
        <Modal title="Add Sync Policy" onClose={() => setShowAdd(false)} size="sm">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div>
              <label className="form-label" style={{ display: 'block', marginBottom: '6px' }}>
                Destination
              </label>
              <div className="select-wrap">
                <select
                  className="form-input"
                  value={form.destination}
                  onChange={(e) => setForm({ ...form, destination: e.target.value })}
                >
                  <option value="sharepoint">SharePoint</option>
                  <option value="teams" disabled>Microsoft Teams (Phase 4)</option>
                </select>
              </div>
            </div>

            <div>
              <label className="form-label" style={{ display: 'block', marginBottom: '6px' }}>Report Template</label>
              <div className="select-wrap">
                <select
                  className="form-input"
                  value={form.report_template_id ?? ''}
                  onChange={(e) => setForm({ ...form, report_template_id: e.target.value || null })}
                >
                  <option value="">— Select template —</option>
                  {templates.map((t) => (
                    <option key={t.id} value={t.id}>{t.name}</option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="form-label" style={{ display: 'block', marginBottom: '6px' }}>Debounce (seconds)</label>
              <input
                type="number"
                className="form-input"
                value={form.debounce_seconds}
                min={10}
                max={3600}
                onChange={(e) => setForm({ ...form, debounce_seconds: Number(e.target.value) })}
              />
            </div>

            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', paddingTop: '4px' }}>
              <button className="btn btn-ghost" onClick={() => setShowAdd(false)}>Cancel</button>
              <button
                className="btn btn-accent"
                onClick={handleAdd}
                disabled={createPolicy.isPending || !form.report_template_id}
              >
                {createPolicy.isPending ? 'Creating…' : 'Create Policy'}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}
