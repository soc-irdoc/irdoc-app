// Evidence register (#150). Mirrors backend/app/schemas/evidence.py.

export type EvidenceKind = 'timeline' | 'incident'

export interface EvidenceSource {
  entry_id: string
  entry_type: string
  occurred_at: string
  excerpt: string
}

export interface EvidenceAssetChip {
  id: string
  name: string
  asset_type: string
}

export interface EvidenceIOCMatch {
  id: string
  ioc_type: string
  value: string
}

export interface EvidenceFile {
  id: string
  kind: EvidenceKind
  original_name: string
  mime_type: string | null
  file_size: number | null
  sha256: string
  is_screenshot: boolean
  uploaded_by: string | null
  uploaded_by_name: string | null
  uploaded_at: string
  source: EvidenceSource | null
  /** null when the user may not read assets */
  assets: EvidenceAssetChip[] | null
  /** null when the user may not read IOCs */
  ioc_matches: EvidenceIOCMatch[] | null
  // IOCs linked to the file's timeline entry (#152); null without IOC access
  linked_iocs?: EvidenceIOCMatch[] | null
}

export interface EvidenceIOC {
  id: string
  ioc_type: string
  value: string
  tlp_level: string
  linked_entries: EvidenceSource[]
  file_count: number
  matching_files: string[]
}
