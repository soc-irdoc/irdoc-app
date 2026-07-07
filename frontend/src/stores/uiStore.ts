import { create } from 'zustand'

export type ToastType = 'success' | 'error' | 'info' | 'warning'

export interface Toast {
  id: string
  message: string
  type: ToastType
}

export interface PresenceUser {
  id: string
  full_name: string
  avatar_initials: string
}

interface UIStore {
  toasts: Toast[]
  addToast: (message: string, type?: ToastType) => void
  removeToast: (id: string) => void
  activeModal: string | null
  openModal: (name: string) => void
  closeModal: () => void
  wsConnected: boolean
  setWsConnected: (connected: boolean) => void
  incidentPresence: Record<string, PresenceUser[]>
  setIncidentPresence: (incidentId: string, users: PresenceUser[]) => void
}

export const useUIStore = create<UIStore>((set) => ({
  toasts: [],
  addToast: (message, type = 'info') => {
    const id = Math.random().toString(36).slice(2)
    set((state) => ({ toasts: [...state.toasts, { id, message, type }] }))
    setTimeout(() => {
      set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) }))
    }, 4000)
  },
  removeToast: (id) =>
    set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),
  activeModal: null,
  openModal: (name) => set({ activeModal: name }),
  closeModal: () => set({ activeModal: null }),
  wsConnected: true,
  setWsConnected: (connected) => set({ wsConnected: connected }),
  incidentPresence: {},
  setIncidentPresence: (incidentId, users) =>
    set((state) => ({
      incidentPresence: { ...state.incidentPresence, [incidentId]: users },
    })),
}))
