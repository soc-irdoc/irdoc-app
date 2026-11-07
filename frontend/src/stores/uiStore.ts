import { create } from 'zustand'

export type ToastType = 'success' | 'error' | 'info' | 'warning'

export interface Toast {
  id: string
  message: string
  type: ToastType
}

export interface ToastOptions {
  /** Milliseconds before auto-dismiss. `Infinity` keeps the toast until the user closes it. */
  duration?: number
}

/** Errors stay until dismissed so the reason can be read (#139); the rest fade out. */
export const DEFAULT_TOAST_DURATION: Record<ToastType, number> = {
  success: 4000,
  info: 4000,
  warning: 6000,
  error: Infinity,
}

/** Oldest toasts are dropped beyond this, so persistent errors can't pile up off-screen. */
export const MAX_TOASTS = 5

export interface PresenceUser {
  id: string
  full_name: string
  avatar_initials: string
}

interface UIStore {
  toasts: Toast[]
  addToast: (message: string, type?: ToastType, opts?: ToastOptions) => void
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
  addToast: (message, type = 'info', opts) => {
    const id = Math.random().toString(36).slice(2)
    set((state) => {
      // An identical message already on screen is replaced, not stacked.
      const others = state.toasts.filter((t) => !(t.message === message && t.type === type))
      return { toasts: [...others, { id, message, type }].slice(-MAX_TOASTS) }
    })
    const duration = opts?.duration ?? DEFAULT_TOAST_DURATION[type]
    if (Number.isFinite(duration)) {
      setTimeout(() => {
        set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) }))
      }, duration)
    }
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
