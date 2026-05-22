import { create } from 'zustand'
import type { User } from '@/types/user'

interface AuthStore {
  user: User | null
  accessToken: string | null
  setAuth: (user: User, token: string) => void
  setToken: (token: string) => void
  setUser: (user: User) => void
  clearAuth: () => void
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  accessToken: null,
  setAuth: (user, accessToken) => set({ user, accessToken }),
  setToken: (accessToken) => set({ accessToken }),
  setUser: (user) => set({ user }),
  clearAuth: () => set({ user: null, accessToken: null }),
}))
