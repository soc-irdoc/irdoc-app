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
    refetchInterval: (query) =>
      (query.state.data as BackupConfig | undefined)?.last_backup_status === 'running'
        ? 2000
        : false,
  })
}

export function useBackupRecords() {
  const qc = useQueryClient()
  return useQuery({
    queryKey: ['backup-records'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<BackupRecord[]>>('/admin/backup/backups')
      return res.data.data
    },
    refetchInterval: () => {
      const config = qc.getQueryData<BackupConfig>(['backup-config'])
      return config?.last_backup_status === 'running' ? 2000 : false
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
    onSuccess: () => {
      // Config already shows "running" (set by the API before dispatching the
      // task), so refetchInterval activates immediately on the next fetch.
      qc.invalidateQueries({ queryKey: ['backup-config'] })
      qc.invalidateQueries({ queryKey: ['backup-records'] })
    },
  })
}
