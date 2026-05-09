import { io, Socket } from 'socket.io-client'
import { useAuthStore } from '@/stores/authStore'
import { useUIStore } from '@/stores/uiStore'

let socket: Socket | null = null
let disconnectTimer: ReturnType<typeof setTimeout> | null = null

function clearDisconnectTimer() {
  if (disconnectTimer !== null) {
    clearTimeout(disconnectTimer)
    disconnectTimer = null
  }
}

export function getSocket(): Socket {
  if (!socket) {
    socket = io('/', {
      path: '/socket.io',
      auth: () => ({ token: useAuthStore.getState().accessToken }),
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    })

    socket.on('connect', () => {
      clearDisconnectTimer()
      useUIStore.getState().setWsConnected(true)
    })

    socket.on('disconnect', () => {
      // Only show the banner after 4 s — transient reconnects stay invisible
      disconnectTimer = setTimeout(() => {
        useUIStore.getState().setWsConnected(false)
      }, 4000)
    })

    socket.on('connect_error', () => {
      if (disconnectTimer === null) {
        disconnectTimer = setTimeout(() => {
          useUIStore.getState().setWsConnected(false)
        }, 4000)
      }
    })

    socket.on('reconnect', () => {
      clearDisconnectTimer()
      useUIStore.getState().setWsConnected(true)
    })

    socket.on('reconnect_failed', () => {
      clearDisconnectTimer()
      useUIStore.getState().setWsConnected(false)
    })

    socket.on('presence:update', ({ incident_id, users }: { incident_id: string; users: import('@/stores/uiStore').PresenceUser[] }) => {
      useUIStore.getState().setIncidentPresence(incident_id, users)
    })
  }
  return socket
}

export function joinIncident(incidentId: string) {
  const user = useAuthStore.getState().user
  const presenceUser = user
    ? {
        id: user.id,
        full_name: user.full_name,
        avatar_initials: user.full_name
          .split(' ')
          .map((p) => p[0])
          .join('')
          .slice(0, 2)
          .toUpperCase(),
      }
    : null

  getSocket().emit('join:incident', { incident_id: incidentId, user: presenceUser })
}

export function leaveIncident(incidentId: string) {
  getSocket().emit('leave:incident', { incident_id: incidentId })
}

export function disconnectSocket() {
  clearDisconnectTimer()
  if (socket) {
    socket.disconnect()
    socket = null
  }
}
