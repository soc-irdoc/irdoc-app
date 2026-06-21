import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import apiClient from '@/lib/apiClient'
import type { TimelineEntry, CreateTimelineEntryPayload, UpdateTimelineEntryPayload, EntryType } from '@/types/timeline'
import type { ApiResponse } from '@/types/api'

export function useTimeline(incidentId: string, filters?: { entry_type?: EntryType }) {
  return useQuery({
    queryKey: ['timeline', incidentId, filters],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<TimelineEntry[]>>(
        `/incidents/${incidentId}/timeline`,
        { params: filters }
      )
      return res.data.data
    },
    enabled: !!incidentId,
  })
}

export function useCreateTimelineEntry(incidentId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (payload: CreateTimelineEntryPayload) => {
      const res = await apiClient.post<ApiResponse<TimelineEntry>>(
        `/incidents/${incidentId}/timeline`,
        payload
      )
      return res.data.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['timeline', incidentId] })
      qc.invalidateQueries({ queryKey: ['incident-stats', incidentId] })
    },
  })
}

export function useUpdateTimelineEntry(incidentId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ entryId, payload }: { entryId: string; payload: UpdateTimelineEntryPayload }) => {
      const res = await apiClient.put<ApiResponse<TimelineEntry>>(
        `/incidents/${incidentId}/timeline/${entryId}`,
        payload
      )
      return res.data.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['timeline', incidentId] })
    },
  })
}

export function useDeleteTimelineEntry(incidentId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (entryId: string) => {
      await apiClient.delete(`/incidents/${incidentId}/timeline/${entryId}`)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['timeline', incidentId] })
      qc.invalidateQueries({ queryKey: ['incident-stats', incidentId] })
    },
  })
}

export function usePinTimelineEntry(incidentId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ entryId, pinned }: { entryId: string; pinned: boolean }) => {
      const res = await apiClient.put<ApiResponse<TimelineEntry>>(
        `/incidents/${incidentId}/timeline/${entryId}`,
        { is_pinned: pinned }
      )
      return res.data.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['timeline', incidentId] })
    },
  })
}

export function useUploadAttachment(incidentId: string, entryId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (file: File) => {
      const fd = new FormData()
      fd.append('file', file)
      fd.append('timeline_entry_id', entryId)
      const res = await apiClient.post(
        `/incidents/${incidentId}/attachments`,
        fd,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      )
      return res.data.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['timeline', incidentId] })
    },
  })
}
