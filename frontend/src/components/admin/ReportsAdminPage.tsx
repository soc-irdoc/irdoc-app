import { useNavigate } from 'react-router-dom'
import { useReportTemplates } from '@/hooks/useReportTemplates'

export function ReportsAdminPage() {
  const navigate = useNavigate()
  const { data: templates = [], isLoading } = useReportTemplates()

  const orgTemplates = templates.filter((t) => !t.is_system)

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: 28 }}>
      <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'Syne, sans-serif', marginBottom: 6 }}>
        Report Templates
      </div>
      <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 28, lineHeight: 1.6 }}>
        Build custom PDF report layouts using the drag-and-drop report builder.
        Set your brand colours, logo, and choose which sections to include.
      </p>

      <section style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderRadius: 12,
        padding: 20,
        marginBottom: 24,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>
            <img src="/icons/card_index_dividers_color.svg" width={20} height={20} alt="" aria-hidden="true" style={{ verticalAlign: 'middle', marginRight: 6 }} />Your Templates
          </h3>
          <button
            className="btn btn-accent btn-sm"
            onClick={() => navigate('/report-templates')}
          >
            Manage Templates →
          </button>
        </div>

        {isLoading ? (
          <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>Loading…</p>
        ) : orgTemplates.length === 0 ? (
          <div style={{
            padding: '32px 20px',
            textAlign: 'center',
            border: '1px dashed var(--border)',
            borderRadius: 10,
            color: 'var(--text-muted)',
            fontSize: 13,
          }}>
            No custom templates yet.{' '}
            <button
              className="btn btn-ghost btn-sm"
              style={{ display: 'inline', padding: '0 4px', textDecoration: 'underline' }}
              onClick={() => navigate('/report-templates/new')}
            >
              Create your first template
            </button>
            {' '}or clone a system template from the builder.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {orgTemplates.map((t) => (
              <div
                key={t.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                  padding: '10px 14px',
                  background: 'var(--bg-base)',
                  border: `1px solid ${t.is_default ? 'var(--accent)' : 'var(--border-subtle)'}`,
                  borderRadius: 8,
                }}
              >
                {t.logo_data_uri ? (
                  <img
                    src={t.logo_data_uri}
                    alt=""
                    style={{ height: '24px', width: 'auto', objectFit: 'contain', flexShrink: 0 }}
                  />
                ) : (
                  <img src="/icons/clipboard_color.svg" width={16} height={16} alt="" aria-hidden="true" style={{ flexShrink: 0 }} />
                )}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
                      {t.name}
                    </span>
                    {t.is_default && (
                      <span className="chip chip-green" style={{ fontSize: 10 }}>DEFAULT</span>
                    )}
                  </div>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    {t.schema_json.length} block{t.schema_json.length !== 1 ? 's' : ''}
                    {t.company_name ? ` · ${t.company_name}` : ''}
                  </span>
                </div>
                <button
                  className="btn btn-ghost btn-sm"
                  onClick={() => navigate(`/report-templates/${t.id}`)}
                >
                  Edit
                </button>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
