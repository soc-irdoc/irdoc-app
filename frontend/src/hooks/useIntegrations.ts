import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import apiClient from '@/lib/apiClient'
import type { Integration } from '@/types/integration'

// ── Queries ──────────────────────────────────────────────────────────────────

export function useIntegrations() {
  return useQuery<Integration[]>({
    queryKey: ['integrations'],
    queryFn: async () => {
      const res = await apiClient.get('/integrations')
      return res.data.data
    },
  })
}

// ── Mutations ────────────────────────────────────────────────────────────────

export function useSaveIntegrationConfig() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ pluginName, config }: { pluginName: string; config: Record<string, string> }) => {
      const res = await apiClient.put(`/integrations/${pluginName}`, { config })
      return res.data.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['integrations'] })
    },
  })
}

export function useTestIntegration() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (pluginName: string) => {
      const res = await apiClient.post(`/integrations/${pluginName}/test`)
      return res.data.data as { ok: boolean; error: string | null }
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['integrations'] })
    },
  })
}

export function useToggleIntegration() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ pluginName, enabled }: { pluginName: string; enabled: boolean }) => {
      const res = await apiClient.post(`/integrations/${pluginName}/toggle`, { enabled })
      return res.data.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['integrations'] })
    },
  })
}

export function usePullSentinelAlerts() {
  return useMutation({
    mutationFn: async (params: { incident_id: string; kql?: string; since_hours?: number }) => {
      const res = await apiClient.post('/integrations/sentinel/pull', params)
      return res.data.data as object[]
    },
  })
}
