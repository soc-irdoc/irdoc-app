import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import apiClient from '@/lib/apiClient'
import type { IOC, CreateIOCPayload, UpdateIOCPayload, DetectedIOC } from '@/types/ioc'
import type { ApiResponse } from '@/types/api'

export function useIOCs(incidentId: string) {
  return useQuery({
    queryKey: ['iocs', incidentId],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<IOC[]>>(`/incidents/${incidentId}/iocs`)
      return res.data.data
    },
    enabled: !!incidentId,
  })
}

export function useCreateIOC(incidentId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (payload: CreateIOCPayload) => {
      const res = await apiClient.post<{ data: IOC; meta: { enrichment_queued: boolean }; error: null }>(
        `/incidents/${incidentId}/iocs`,
        payload
      )
      return { ioc: res.data.data, enrichment_queued: res.data.meta?.enrichment_queued ?? false }
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['iocs', incidentId] })
      qc.invalidateQueries({ queryKey: ['incident-stats', incidentId] })
    },
  })
}

export function useUpdateIOC(incidentId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ iocId, payload }: { iocId: string; payload: UpdateIOCPayload }) => {
      const res = await apiClient.put<ApiResponse<IOC>>(
        `/incidents/${incidentId}/iocs/${iocId}`,
        payload
      )
      return res.data.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['iocs', incidentId] })
    },
  })
}

export function useDeleteIOC(incidentId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (iocId: string) => {
      await apiClient.delete(`/incidents/${incidentId}/iocs/${iocId}`)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['iocs', incidentId] })
      qc.invalidateQueries({ queryKey: ['incident-stats', incidentId] })
    },
  })
}

export function useBulkImportIOCs(incidentId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (text: string) => {
      const res = await apiClient.post<{ data: IOC[]; meta: { enrichment_queued: boolean }; error: null }>(
        `/incidents/${incidentId}/iocs/bulk`,
        { text }
      )
      return { iocs: res.data.data, enrichment_queued: res.data.meta?.enrichment_queued ?? false }
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['iocs', incidentId] })
      qc.invalidateQueries({ queryKey: ['incident-stats', incidentId] })
    },
  })
}

export function useDetectIOCs(incidentId: string) {
  return useMutation({
    mutationFn: async (text: string) => {
      const res = await apiClient.post<DetectedIOC[]>(
        `/incidents/${incidentId}/iocs/detect`,
        { text }
      )
      return res.data
    },
  })
}
