import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import apiClient from '@/lib/apiClient'
import type { APIKey, CreateAPIKeyPayload, CreatedAPIKeyResponse } from '@/types/apiKey'
import type { ApiResponse } from '@/types/api'

export function useAPIKeys() {
  return useQuery({
    queryKey: ['api-keys'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<APIKey[]>>('/api-keys')
      return res.data.data
    },
  })
}

export function useCreateAPIKey() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (payload: CreateAPIKeyPayload) => {
      const res = await apiClient.post<ApiResponse<CreatedAPIKeyResponse>>('/api-keys', payload)
      return res.data.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['api-keys'] })
    },
  })
}

export function useRevokeAPIKey() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (keyId: string) => {
      await apiClient.delete(`/api-keys/${keyId}`)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['api-keys'] })
    },
  })
}
