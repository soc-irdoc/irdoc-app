export interface SmtpConfig {
  is_enabled: boolean
  host: string | null
  port: number
  use_tls: boolean
  username: string | null
  password: string // "••••••" if set, "" if not
  from_name: string | null
  from_address: string | null
  subject_template: string
  logo_url: string | null
  accent_color: string
  footer_text: string | null
}

export interface SmtpConfigPayload {
  is_enabled?: boolean
  host?: string
  port?: number
  use_tls?: boolean
  username?: string
  password?: string | null // null = keep existing
  from_name?: string
  from_address?: string
  subject_template?: string
  logo_url?: string | null
  accent_color?: string
  footer_text?: string | null
}

export interface SmtpTestPayload {
  host: string
  port: number
  use_tls: boolean
  username?: string | null
  password?: string | null
  from_name?: string | null
  from_address?: string | null
}

export interface SmtpTestResult {
  ok: boolean
  error: string | null
}
