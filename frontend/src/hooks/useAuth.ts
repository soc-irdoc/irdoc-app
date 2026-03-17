import { useMutation } from '@tanstack/react-query'
import apiClient from '@/lib/apiClient'
import { useAuthStore } from '@/stores/authStore'
import type { User } from '@/types/user'

interface LoginPayload {
  email: string
  password: string
}

// Backend response shape: { data: { access_token, token_type }, user: { ... } }
interface LoginApiResponse {
  data: { access_token: string }
  user: User
}

export function useLogin() {
  const setAuth = useAuthStore((s) => s.setAuth)

  return useMutation({
    mutationFn: async (payload: LoginPayload) => {
      const res = await apiClient.post<LoginApiResponse>('/auth/login', payload)
      return { user: res.data.user, access_token: res.data.data.access_token }
    },
    onSuccess: (data) => {
      setAuth(data.user, data.access_token)
    },
  })
}

export function useLogout() {
  const clearAuth = useAuthStore((s) => s.clearAuth)

  return useMutation({
    mutationFn: async () => {
      await apiClient.post('/auth/logout')
    },
    onSuccess: () => {
      clearAuth()
    },
    onError: () => {
      clearAuth()
    },
  })
}

export function useChangePassword() {
  return useMutation({
    mutationFn: async (payload: { current_password: string; new_password: string }) => {
      const res = await apiClient.post('/auth/change-password', payload)
      return res.data
    },
  })
}
