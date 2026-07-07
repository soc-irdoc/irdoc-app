import { useQuery } from '@tanstack/react-query'
import { versionApi } from '@/lib/apiClient'
import { useAuthStore } from '@/stores/authStore'

export function useVersion() {
  const user = useAuthStore((s) => s.user)

  const query = useQuery({
    queryKey: ['version'],
    queryFn: async () => {
      const res = await versionApi.get()
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
