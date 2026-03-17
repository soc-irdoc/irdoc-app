export type UserRole = 'admin' | 'senior_analyst' | 'analyst' | 'viewer'

export interface User {
  id: string
  org_id: string
  email: string
  full_name: string
  role: UserRole
  timezone: string
  theme: 'dark' | 'light'
  is_active: boolean
  must_reset_password: boolean
}
