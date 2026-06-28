import { useMutation } from '@tanstack/react-query'
import apiClient, { cancelTokenTimers } from '@/lib/apiClient'
import { useAuthStore } from '@/stores/authStore'
import { disconnectSocket } from '@/lib/websocket'
import type { User } from '@/types/user'

interface LoginPayload {
  email: string
  password: string
}

export interface LoginResult {
  access_token?: string
  mfa_challenge_token?: string
  mfa_setup_token?: string
  user?: User
}

export function useLogin() {
  const setAuth = useAuthStore((s) => s.setAuth)

  return useMutation({
    mutationFn: async (payload: LoginPayload): Promise<LoginResult> => {
      const res = await apiClient.post<{ data: LoginResult }>('/auth/login', payload)
      return res.data.data
    },
    onSuccess: (data) => {
      if (data.access_token && data.user) {
        setAuth(data.user, data.access_token)
      }
    },
  })
}

export function useLogout() {
  const clearAuth = useAuthStore((s) => s.clearAuth)

  return useMutation({
    mutationFn: async () => {
      cancelTokenTimers()
      disconnectSocket()
      await apiClient.post('/auth/logout')
    },
    onSuccess: () => {
      clearAuth()
    },
    onError: () => {
      cancelTokenTimers()
      disconnectSocket()
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
