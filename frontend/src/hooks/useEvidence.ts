import { keepPreviousData, useQuery } from '@tanstack/react-query'
import apiClient from '@/lib/apiClient'
import type { ApiResponse } from '@/types/api'
import type { EvidenceFile, EvidenceIOC } from '@/types/evidence'
import { toEvidenceApiParams, type EvidenceQuery } from '@/lib/evidenceQuery'

// Keys start with ['evidence', incidentId] so uploads/deletes on the
// timeline can invalidate them all.
export function useEvidenceFiles(incidentId: string, query: EvidenceQuery, enabled = true) {
  const params = { ...toEvidenceApiParams(query), page: query.page, per_page: query.perPage }
  return useQuery({
    queryKey: ['evidence', incidentId, 'files', params],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<EvidenceFile[]>>(`/incidents/${incidentId}/evidence`, { params })
      return res.data
    },
    placeholderData: keepPreviousData,
    enabled: !!incidentId && enabled,
  })
}

export function useEvidenceIOCs(incidentId: string, enabled = true) {
  return useQuery({
    queryKey: ['evidence', incidentId, 'iocs'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<EvidenceIOC[]>>(`/incidents/${incidentId}/evidence/iocs`)
      return res.data.data
    },
    enabled: !!incidentId && enabled,
  })
}
