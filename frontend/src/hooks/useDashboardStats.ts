import { useQuery } from '@tanstack/react-query'
import apiClient from '@/lib/apiClient'
import type { DashboardStats } from '@/types/dashboard'
import type { ApiResponse } from '@/types/api'

export function useDashboardStats(from_dt: string, to_dt: string) {
  return useQuery({
    queryKey: ['dashboard', 'stats', from_dt, to_dt],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<DashboardStats>>('/dashboard/stats', {
        params: { from_dt, to_dt },
      })
      return res.data.data
    },
    staleTime: 60_000,
  })
}
