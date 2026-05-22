export interface ApiResponse<T> {
  data: T
  meta: {
    page?: number
    per_page?: number
    total?: number
  }
  error: string | null
}

export interface PaginatedMeta {
  page: number
  per_page: number
  total: number
}

export interface LoginResponse {
  access_token?: string
  token_type?: string
  mfa_challenge_token?: string
  mfa_setup_token?: string
  user?: import('./user').User
}
