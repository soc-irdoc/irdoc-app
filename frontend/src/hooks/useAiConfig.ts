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

export const AI_DISABLED_HINT = 'Local AI (Ollama) is disabled. Enable it in Integrations → Local AI.'

/**
 * Whether Local AI (Ollama) is enabled for the org. Readable by every role.
 * `disabled` is true only once the server has confirmed AI is off, so AI
 * controls don't flash greyed-out while the status loads.
 */
export function useAiStatus() {
  const query = useQuery({
    queryKey: ['ai-status'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<{ enabled: boolean }>>('/ai/status')
      return res.data.data
    },
    staleTime: 60 * 1000,
  })
  return { enabled: query.data?.enabled ?? false, disabled: query.data?.enabled === false }
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
      qc.invalidateQueries({ queryKey: ['ai-status'] })
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
