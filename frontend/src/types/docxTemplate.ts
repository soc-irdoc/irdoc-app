export interface DocxTemplate {
  id: string
  org_id: string
  name: string
  is_default: boolean
  file_size: number | null
  created_by: string | null
  created_at: string
  updated_at: string
}
