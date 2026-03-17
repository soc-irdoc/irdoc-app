import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import apiClient from '@/lib/apiClient'
import { SyncPolicy, SyncPolicyCreate } from '@/types/report'
import { useUIStore } from '@/stores/uiStore'

export function useSyncPolicies(incidentId: string) {
  return useQuery<SyncPolicy[]>({
    queryKey: ['sync-policies', incidentId],
    queryFn: async () => {
      const { data } = await apiClient.get(`/incidents/${incidentId}/sync-policies`)
      return data.data
    },
    enabled: !!incidentId,
  })
}

export function useCreateSyncPolicy(incidentId: string) {
  const qc = useQueryClient()
  const addToast = useUIStore((s) => s.addToast)

  return useMutation({
    mutationFn: async (payload: SyncPolicyCreate) => {
      const { data } = await apiClient.post(`/incidents/${incidentId}/sync-policies`, payload)
      return data.data as SyncPolicy
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sync-policies', incidentId] })
      addToast('Sync policy created', 'success')
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail || 'Failed to create sync policy'
      addToast(msg, 'error')
    },
  })
}

export function useUpdateSyncPolicy(incidentId: string) {
  const qc = useQueryClient()
  const addToast = useUIStore((s) => s.addToast)

  return useMutation({
    mutationFn: async ({ policyId, data }: { policyId: string; data: Partial<SyncPolicyCreate & { is_active: boolean }> }) => {
      const { data: res } = await apiClient.put(`/incidents/${incidentId}/sync-policies/${policyId}`, data)
      return res.data as SyncPolicy
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sync-policies', incidentId] })
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail || 'Failed to update sync policy'
      addToast(msg, 'error')
    },
  })
}

export function useDeleteSyncPolicy(incidentId: string) {
  const qc = useQueryClient()
  const addToast = useUIStore((s) => s.addToast)

  return useMutation({
    mutationFn: async (policyId: string) => {
      await apiClient.delete(`/incidents/${incidentId}/sync-policies/${policyId}`)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sync-policies', incidentId] })
      addToast('Sync policy removed', 'success')
    },
  })
}

export function useTriggerSyncPolicy(incidentId: string) {
  const addToast = useUIStore((s) => s.addToast)

  return useMutation({
    mutationFn: async (policyId: string) => {
      const { data } = await apiClient.post(
        `/incidents/${incidentId}/sync-policies/${policyId}/trigger`
      )
      return data
    },
    onSuccess: () => {
      addToast('Sync queued', 'info')
    },
  })
}
