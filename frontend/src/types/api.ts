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
