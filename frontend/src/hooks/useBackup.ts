import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import apiClient from '@/lib/apiClient'
import type { BackupConfig, BackupConfigUpdate, BackupRecord } from '@/types/backup'
import type { ApiResponse } from '@/types/api'

export function useBackupConfig() {
  return useQuery({
    queryKey: ['backup-config'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<BackupConfig>>('/admin/backup/config')
      return res.data.data
    },
  })
}

export function useBackupRecords() {
  return useQuery({
    queryKey: ['backup-records'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<BackupRecord[]>>('/admin/backup/backups')
      return res.data.data
    },
  })
}

export function useUpdateBackupConfig() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (payload: BackupConfigUpdate) => {
      const res = await apiClient.put<ApiResponse<BackupConfig>>('/admin/backup/config', payload)
      return res.data.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['backup-config'] })
    },
  })
}

export function useTriggerBackup() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const res = await apiClient.post<ApiResponse<null>>('/admin/backup/run')
      return res.data.data
    },
    onSuccess: async () => {
      // Wait for the Celery task to start and update status before refreshing
      await new Promise(r => setTimeout(r, 3000))
      qc.invalidateQueries({ queryKey: ['backup-config'] })
      qc.invalidateQueries({ queryKey: ['backup-records'] })
    },
  })
}
