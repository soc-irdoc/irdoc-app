import { useState, useEffect } from 'react'
import { useAiConfig, useSaveAiConfig, useTestAiConfig } from '@/hooks/useAiConfig'
import { useUIStore } from '@/stores/uiStore'
import { ToggleSwitch } from '@/components/common/ToggleSwitch'

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
  ollamaBaseUrl: string
  modelName: string
  debounceSeconds: number
  maxTimelineEvents: number
}

const DEFAULT_STATE: FormState = {
  isEnabled: false,
  ollamaBaseUrl: 'http://ollama:11434',
  modelName: 'llama3.2',
  debounceSeconds: 60,
  maxTimelineEvents: 20,
}

interface TestResult {
  success: boolean
  error: string | null
  available_models?: string[]
}

export function AiSection() {
  const addToast = useUIStore((s) => s.addToast)
  const { data: config } = useAiConfig()
  const saveConfig = useSaveAiConfig()
  const testConfig = useTestAiConfig()

  const [expanded, setExpanded] = useState(false)
  const [form, setForm] = useState<FormState>(DEFAULT_STATE)
  const [testResult, setTestResult] = useState<TestResult | null>(null)

  useEffect(() => {
    if (!config) return
    setForm({
      isEnabled: config.is_enabled,
      ollamaBaseUrl: config.ollama_base_url,
      modelName: config.model_name,
      debounceSeconds: config.debounce_seconds,
      maxTimelineEvents: config.max_timeline_events,
    })
  }, [config])

  const set = (key: keyof FormState) => (value: FormState[typeof key]) =>
    setForm((prev) => ({ ...prev, [key]: value }))

  const statusColor = config?.is_enabled ? 'var(--green)' : 'var(--text-muted)'
  const statusText = config?.is_enabled
    ? `Enabled — ${config.model_name} via ${config.ollama_base_url}`
    : 'Disabled'

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    if (form.isEnabled) {
      if (!form.ollamaBaseUrl.trim()) {
        addToast('Ollama base URL is required to enable AI', 'error')
        return
      }
      if (!form.modelName.trim()) {
        addToast('Model name is required to enable AI', 'error')
        return
      }
    }
    try {
      await saveConfig.mutateAsync({
        is_enabled: form.isEnabled,
        ollama_base_url: form.ollamaBaseUrl,
        model_name: form.modelName,
        debounce_seconds: form.debounceSeconds,
        max_timeline_events: form.maxTimelineEvents,
      })
      addToast('AI configuration saved.', 'success')
      setTestResult(null)
    } catch {
      addToast('Failed to save AI configuration.', 'error')
    }
  }

  async function handleTest() {
    setTestResult(null)
    try {
      const result = await testConfig.mutateAsync({
        ollama_base_url: form.ollamaBaseUrl,
        model_name: form.modelName,
      })
      setTestResult(result ?? { success: false, error: 'No response from server' })
    } catch (err: unknown) {
      setTestResult({ success: false, error: err instanceof Error ? err.message : 'Unknown error' })
    }
  }

  return (
    <div style={{ marginBottom: 32 }} id="ai-section">
      <h3 style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 12 }}>
        AI
      </h3>
      <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 14, marginTop: -8 }}>
        Local AI report generation powered by Ollama. AI narratives are evidence-backed and versioned.
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
            <img src="/icons/robot_color.svg" width={20} height={20} alt="" aria-hidden="true" />
          </div>
          <div style={{ flex: 1 }}>
            <p style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>Local AI (Ollama)</p>
            <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>Air-gapped, evidence-grounded report generation — no cloud required</p>
          </div>
          <ToggleSwitch
            checked={form.isEnabled}
            onChange={(v) => {
              set('isEnabled')(v)
              if (v) setExpanded(true)
            }}
            ariaLabel="Enable AI"
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

              {/* Provider */}
              {subCard('Local AI Provider',
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 10 }}>
                    <div>
                      {subLabel('Ollama Base URL')}
                      <input
                        className="form-input"
                        type="text"
                        placeholder="http://ollama:11434"
                        value={form.ollamaBaseUrl}
                        onChange={(e) => set('ollamaBaseUrl')(e.target.value)}
                      />
                      <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4 }}>
                        Default <code style={{ background: 'var(--bg-elevated)', padding: '1px 4px', borderRadius: 3 }}>http://ollama:11434</code> works with the bundled docker-compose profile.
                        Use <code style={{ background: 'var(--bg-elevated)', padding: '1px 4px', borderRadius: 3 }}>http://host.docker.internal:11434</code> for native Ollama on Mac/Windows.
                      </div>
                    </div>
                    <div>
                      {subLabel('Model Name')}
                      <input
                        className="form-input"
                        type="text"
                        placeholder="llama3.2"
                        value={form.modelName}
                        onChange={(e) => set('modelName')(e.target.value)}
                      />
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, flexWrap: 'wrap' }}>
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      onClick={handleTest}
                      disabled={testConfig.isPending || !form.ollamaBaseUrl}
                      style={{ display: 'flex', alignItems: 'center', gap: 6 }}
                    >
                      {testConfig.isPending ? 'Testing…' : <><img src="/icons/electric_plug_color.svg" width={14} height={14} alt="" aria-hidden="true" style={{ verticalAlign: 'middle', marginRight: 4 }} />Test Connection</>}
                    </button>

                    {testResult && (
                      <div style={{
                        padding: '6px 12px',
                        borderRadius: 6,
                        fontSize: 11,
                        flex: 1,
                        background: testResult.success ? 'rgba(34,197,94,0.08)' : 'rgba(239,68,68,0.08)',
                        color: testResult.success ? 'var(--green)' : 'var(--red)',
                        border: `1px solid ${testResult.success ? 'var(--green)' : 'var(--red)'}`,
                        lineHeight: 1.6,
                      }}>
                        {testResult.success
                          ? `✓ Connected — model "${form.modelName}" is available`
                          : `✗ ${testResult.error}`}
                        {!testResult.success && testResult.error?.includes('ollama pull') && (
                          <div style={{ marginTop: 6, background: 'var(--bg-elevated)', borderRadius: 4, padding: '4px 8px', fontFamily: 'monospace', fontSize: 10, color: 'var(--text-primary)', wordBreak: 'break-all' }}>
                            {testResult.error?.match(/docker compose.*ollama pull .+/)?.[0] ?? `ollama pull ${form.modelName}`}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Report Generation */}
              {subCard('Report Generation',
                <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                    <div>
                      {subLabel('Debounce Delay (seconds)')}
                      <input
                        className="form-input"
                        type="number"
                        min={10}
                        max={3600}
                        value={form.debounceSeconds}
                        onChange={(e) => set('debounceSeconds')(Math.min(3600, Math.max(10, parseInt(e.target.value, 10) || 60)))}
                      />
                      <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4 }}>
                        AI report regenerates this many seconds after the last incident update. Min 10s, max 3600s.
                      </div>
                    </div>
                    <div>
                      {subLabel('Max Timeline Events')}
                      <input
                        className="form-input"
                        type="number"
                        min={1}
                        max={200}
                        value={form.maxTimelineEvents}
                        onChange={(e) => set('maxTimelineEvents')(Math.min(200, Math.max(1, parseInt(e.target.value, 10) || 20)))}
                      />
                      <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4 }}>
                        Limits timeline events in the AI prompt. Decrease if your model has a small context window.
                      </div>
                    </div>
                  </div>

                  <div style={{
                    background: 'rgba(99,102,241,0.06)',
                    border: '1px solid rgba(99,102,241,0.2)',
                    borderRadius: 8,
                    padding: '10px 14px',
                    fontSize: 12,
                    color: 'var(--text-secondary)',
                    lineHeight: 1.6,
                  }}>
                    <strong style={{ color: 'var(--text-primary)' }}>Version history:</strong> Each AI generation creates a new versioned report.
                    Previous versions are never overwritten — all are preserved for audit and traceability.
                    New reports are delta-aware: the AI reviews the previous narrative before writing the next one.
                  </div>
                </div>
              )}
            </div>

            {/* Save bar */}
            <div style={{ padding: '14px 20px 20px', display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => setExpanded(false)}>Collapse</button>
              <button type="submit" className="btn btn-accent btn-sm" disabled={saveConfig.isPending}>
                {saveConfig.isPending ? 'Saving…' : 'Save AI Configuration'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
