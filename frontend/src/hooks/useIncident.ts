import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import apiClient from '@/lib/apiClient'
import type { Incident, CreateIncidentPayload, UpdateIncidentPayload, IncidentStats } from '@/types/incident'
import type { ApiResponse } from '@/types/api'

export function useIncidents(params?: {
  status?: string
  search?: string
  page?: number
  per_page?: number
}) {
  return useQuery({
    queryKey: ['incidents', params],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<Incident[]>>('/incidents', { params })
      return res.data
    },
  })
}

export function useIncident(id: string) {
  return useQuery({
    queryKey: ['incident', id],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<Incident>>(`/incidents/${id}`)
      return res.data.data
    },
    enabled: !!id,
  })
}

export function useIncidentStats(id: string) {
  return useQuery({
    queryKey: ['incident-stats', id],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<IncidentStats>>(`/incidents/${id}/stats`)
      return res.data.data
    },
    enabled: !!id,
  })
}

export function useCreateIncident() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (payload: CreateIncidentPayload) => {
      const res = await apiClient.post<ApiResponse<Incident>>('/incidents', payload)
      return res.data.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['incidents'] })
    },
  })
}

export function useUpdateIncident(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (payload: UpdateIncidentPayload) => {
      const res = await apiClient.put<ApiResponse<Incident>>(`/incidents/${id}`, payload)
      return res.data.data
    },
    onSuccess: (data) => {
      qc.setQueryData(['incident', id], data)
      qc.invalidateQueries({ queryKey: ['incidents'] })
    },
  })
}

export function useIncidentTemplates() {
  return useQuery({
    queryKey: ['incident-templates'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<Array<{ id: string; name: string; slug: string }>>>('/templates/incidents')
      return res.data.data
    },
  })
}
