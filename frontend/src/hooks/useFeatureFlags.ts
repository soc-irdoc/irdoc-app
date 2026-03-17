import { useQuery } from '@tanstack/react-query'
import apiClient from '@/lib/apiClient'
import { useAuthStore } from '@/stores/authStore'

interface FeatureFlags {
  [key: string]: boolean
}

export function useFeatureFlags() {
  const user = useAuthStore((s) => s.user)

  const query = useQuery({
    queryKey: ['features'],
    queryFn: async () => {
      const res = await apiClient.get<{ data: FeatureFlags }>('/features')
      return res.data.data
    },
    enabled: !!user,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  return {
    flags: query.data ?? {},
    isLoading: query.isLoading,
    hasFeature: (feature: string) => query.data?.[feature] ?? false,
  }
}
