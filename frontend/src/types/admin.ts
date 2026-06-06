export interface OrgUser {
  id: string
  email: string
  full_name: string
  role: 'admin' | 'senior_analyst' | 'analyst' | 'viewer'
  is_active: boolean
  mfa_enabled: boolean
  created_at: string
}

export interface UserInvite {
  id: string
  email: string
  role: string
  expires_at: string
  accepted_at: string | null
  invited_by_name: string
}

export interface OrgSettings {
  id: string
  name: string
  slug: string
  plan: string
  allow_registration: boolean
  mfa_required?: boolean
  logo_url?: string
  accent_color?: string
}

export interface StorageConfigOut {
  backend: 'local' | 's3' | 'azure_blob' | 'gcs'
  is_active: boolean
  created_at: string
}

export interface SSOConfig {
  id: string
  org_id: string
  provider: string
  is_enabled: boolean
  idp_metadata_url: string | null
  entity_id: string | null
  sso_url: string | null
  attr_email: string | null
  attr_name: string | null
  attr_groups: string | null
  role_mappings: Record<string, string>
}

export interface AuditLogEntry {
  id: string
  action: string
  entity_type: string | null
  entity_id: string | null
  user_id: string | null
  api_key_id: string | null
  ip_address: string | null
  created_at: string
}

export const ROLE_LABELS: Record<string, string> = {
  admin: 'Admin',
  senior_analyst: 'Senior Analyst',
  analyst: 'Analyst',
  viewer: 'Viewer',
}

export const ROLE_COLORS: Record<string, string> = {
  admin: 'chip-red',
  senior_analyst: 'chip-yellow',
  analyst: 'chip-blue',
  viewer: 'chip-muted',
}
