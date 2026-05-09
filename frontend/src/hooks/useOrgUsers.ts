import { useQuery } from '@tanstack/react-query'
import apiClient from '@/lib/apiClient'
import type { ApiResponse } from '@/types/api'
import type { UserBrief } from '@/types/incident'

interface UserListItem extends UserBrief {
  role: string
  is_active: boolean
}

export function useOrgUsers() {
  return useQuery({
    queryKey: ['org-users'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<UserListItem[]>>('/users')
      return res.data.data
    },
    staleTime: 60_000,
  })
}
