import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import apiClient from '@/lib/apiClient'
import type { GraphData } from '@/types/graph'

export function useGraph(incidentId: string) {
  return useQuery<GraphData>({
    queryKey: ['graph', incidentId],
    queryFn: async () => {
      const res = await apiClient.get(`/incidents/${incidentId}/graph`)
      return res.data.data
    },
    staleTime: 30_000, // graph is expensive to build — 30s cache
  })
}

export function useAddGraphEdge(incidentId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (params: { source_node_id: string; target_node_id: string; label?: string }) => {
      const res = await apiClient.post(`/incidents/${incidentId}/graph/edges`, params)
      return res.data.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['graph', incidentId] })
    },
  })
}

export function useDeleteGraphEdge(incidentId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (edgeId: string) => {
      await apiClient.delete(`/incidents/${incidentId}/graph/edges/${edgeId}`)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['graph', incidentId] })
    },
  })
}
