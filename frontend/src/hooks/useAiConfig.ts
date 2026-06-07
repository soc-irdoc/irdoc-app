import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import apiClient from '@/lib/apiClient'
import type { ApiResponse } from '@/types/api'

export interface AiConfig {
  is_enabled: boolean
  ollama_base_url: string
  model_name: string
  debounce_seconds: number
  max_timeline_events: number
}

export interface AiConfigPayload {
  is_enabled?: boolean
  ollama_base_url?: string
  model_name?: string
  debounce_seconds?: number
  max_timeline_events?: number
}

export interface AiTestResult {
  success: boolean
  error: string | null
  available_models?: string[]
}

export function useAiConfig() {
  return useQuery({
    queryKey: ['ai-config'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<AiConfig>>('/admin/ai')
      return res.data.data
    },
  })
}

export function useSaveAiConfig() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (payload: AiConfigPayload) => {
      const res = await apiClient.put<ApiResponse<AiConfig>>('/admin/ai', payload)
      return res.data.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ai-config'] })
    },
  })
}

export function useTestAiConfig() {
  return useMutation({
    mutationFn: async (payload: { ollama_base_url: string; model_name: string }) => {
      const res = await apiClient.post<ApiResponse<AiTestResult>>('/admin/ai/test', payload)
      return res.data.data
    },
  })
}
