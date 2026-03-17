export interface APIKey {
  id: string
  org_id: string
  name: string
  key_prefix: string
  scopes: string[]
  expires_at: string | null
  last_used_at: string | null
  created_at: string
}

export interface CreateAPIKeyPayload {
  name: string
  scopes: string[]
  expires_in_days?: number
}

export interface CreatedAPIKeyResponse extends APIKey {
  raw_key: string
}

export const AVAILABLE_SCOPES = [
  { value: 'incidents:create', label: 'Create incidents' },
  { value: 'incidents:read',   label: 'Read incidents' },
  { value: 'incidents:write',  label: 'Write incidents' },
  { value: 'timeline:read',    label: 'Read timeline' },
  { value: 'iocs:read',        label: 'Read IOCs' },
  { value: 'reports:read',     label: 'Read reports' },
]
