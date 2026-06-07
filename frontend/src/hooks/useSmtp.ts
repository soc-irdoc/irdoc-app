import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import apiClient from '@/lib/apiClient'
import type { SmtpConfig, SmtpConfigPayload, SmtpTestPayload, SmtpTestResult } from '@/types/smtp'
import type { ApiResponse } from '@/types/api'

export function useSmtpConfig() {
  return useQuery({
    queryKey: ['smtp-config'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<SmtpConfig | null>>('/admin/smtp')
      return res.data.data
    },
  })
}

export function useSaveSmtpConfig() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (payload: SmtpConfigPayload) => {
      const res = await apiClient.put<ApiResponse<SmtpConfig>>('/admin/smtp', payload)
      return res.data.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['smtp-config'] })
    },
  })
}

export function useTestSmtp() {
  return useMutation({
    mutationFn: async (payload: SmtpTestPayload) => {
      const res = await apiClient.post<ApiResponse<SmtpTestResult>>('/admin/smtp/test', payload)
      return res.data.data
    },
  })
}
