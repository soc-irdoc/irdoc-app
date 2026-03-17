import { useAuthStore } from '@/stores/authStore'

const ROLE_HIERARCHY: Record<string, number> = {
  viewer: 0,
  analyst: 1,
  senior_analyst: 2,
  admin: 3,
}

export function hasPermission(userRole: string, minimumRole: string): boolean {
  return (ROLE_HIERARCHY[userRole] ?? -1) >= (ROLE_HIERARCHY[minimumRole] ?? 99)
}

export function usePermission(minimumRole: string): boolean {
  const user = useAuthStore((s) => s.user)
  if (!user) return false
  return hasPermission(user.role, minimumRole)
}
