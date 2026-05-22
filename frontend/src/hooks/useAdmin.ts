import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import apiClient from '@/lib/apiClient'
import type {
  OrgUser,
  UserInvite,
  OrgSettings,
  StorageConfigOut,
  SSOConfig,
  AuditLogEntry,
} from '@/types/admin'
import type { ApiResponse } from '@/types/api'

// ── Team management ────────────────────────────────────────

export function useOrgUsers() {
  return useQuery({
    queryKey: ['org-users'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<OrgUser[]>>('/users')
      return res.data.data
    },
  })
}

export function useUpdateUserRole() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, role }: { id: string; role: string }) => {
      const res = await apiClient.put<ApiResponse<OrgUser>>(`/users/${id}/role`, { role })
      return res.data.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['org-users'] })
    },
  })
}

export function useDeactivateUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      const res = await apiClient.put<ApiResponse<OrgUser>>(`/users/${id}/deactivate`, {})
      return res.data.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['org-users'] })
    },
  })
}

export function useResetUserMFA() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (userId: string) => {
      await apiClient.post(`/users/${userId}/mfa/reset`)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['org-users'] })
    },
  })
}

// ── Invites ────────────────────────────────────────────────

export function useInvites() {
  return useQuery({
    queryKey: ['invites'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<UserInvite[]>>('/users/invites')
      return res.data.data
    },
  })
}

export function useSendInvite() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (payload: { email: string; role: string }) => {
      const res = await apiClient.post<ApiResponse<UserInvite>>('/users/invite', payload)
      return res.data.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['invites'] })
    },
  })
}

export function useRevokeInvite() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/users/invites/${id}`)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['invites'] })
    },
  })
}

// ── Org settings ───────────────────────────────────────────

// The backend nests allow_registration and mfa_required inside a `settings` JSONB field.
// Flatten them into the top-level object so callers can read org.mfa_required directly.
function flattenOrgSettings(raw: Record<string, unknown>): OrgSettings {
  const { settings, ...rest } = raw as { settings?: Record<string, unknown> } & Record<string, unknown>
  return { ...rest, ...(settings ?? {}) } as unknown as OrgSettings
}

export function useOrgSettings() {
  return useQuery({
    queryKey: ['org-settings'],
    queryFn: async () => {
      const res = await apiClient.get<{ data: Record<string, unknown> }>('/admin/org')
      return flattenOrgSettings(res.data.data)
    },
  })
}

export function useUpdateOrgSettings() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (payload: Partial<OrgSettings>) => {
      const res = await apiClient.put<{ data: Record<string, unknown> }>('/admin/org', payload)
      return flattenOrgSettings(res.data.data)
    },
    onSuccess: (data) => {
      qc.setQueryData(['org-settings'], data)
    },
  })
}

// ── Storage ────────────────────────────────────────────────

export function useStorageConfig() {
  return useQuery({
    queryKey: ['storage-config'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<StorageConfigOut>>('/admin/storage')
      return res.data.data
    },
  })
}

export function useUpdateStorageConfig() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      const res = await apiClient.put<ApiResponse<StorageConfigOut>>('/admin/storage', payload)
      return res.data.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['storage-config'] })
    },
  })
}

export function useTestStorageConnection() {
  return useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      const res = await apiClient.post<ApiResponse<{ ok: boolean; error: string | null }>>(
        '/admin/storage/test',
        payload
      )
      return res.data.data
    },
  })
}

export function useSwitchStorageBackend() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      const res = await apiClient.post<ApiResponse<StorageConfigOut>>(
        '/admin/storage/switch',
        payload
      )
      return res.data.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['storage-config'] })
    },
  })
}

// ── SSO ────────────────────────────────────────────────────

export function useSSOConfig() {
  return useQuery({
    queryKey: ['sso-config'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<SSOConfig>>('/admin/sso')
      return res.data.data
    },
  })
}

export function useUpdateSSOConfig() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (payload: Partial<SSOConfig>) => {
      const res = await apiClient.put<ApiResponse<SSOConfig>>('/admin/sso', payload)
      return res.data.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sso-config'] })
    },
  })
}

// ── Audit log ──────────────────────────────────────────────

export interface AuditLogFilters {
  action?: string
  from?: string
  to?: string
  page?: number
  per_page?: number
}

export function useAuditLog(filters: AuditLogFilters = {}) {
  return useQuery({
    queryKey: ['audit-log', filters],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<AuditLogEntry[]>>('/audit-log', {
        params: filters,
      })
      return res.data
    },
  })
}

export function useExportAuditLog() {
  return async (filters: AuditLogFilters = {}) => {
    const params = new URLSearchParams()
    if (filters.action) params.set('action', filters.action)
    if (filters.from) params.set('from', filters.from)
    if (filters.to) params.set('to', filters.to)
    const url = `/api/v1/audit-log/export?${params.toString()}`
    const a = document.createElement('a')
    a.href = url
    a.download = `audit-log-${new Date().toISOString().slice(0, 10)}.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }
}
