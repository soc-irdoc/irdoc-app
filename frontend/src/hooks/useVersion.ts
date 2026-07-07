import { useQuery } from '@tanstack/react-query'
import apiClient from '@/lib/apiClient'
import { useAuthStore } from '@/stores/authStore'

interface VersionInfo {
  version: string
  latest_version: string | null
  update_available: boolean
}

export function useVersion() {
  const user = useAuthStore((s) => s.user)

  const query = useQuery({
    queryKey: ['version'],
    queryFn: async () => {
      const res = await apiClient.get<{ data: VersionInfo }>('/version')
      return res.data.data
    },
    enabled: !!user,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  return {
    version: query.data?.version,
    latestVersion: query.data?.latest_version ?? null,
    updateAvailable: query.data?.update_available ?? false,
  }
}
