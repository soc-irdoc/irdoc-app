import { io, Socket } from 'socket.io-client'
import { useAuthStore } from '@/stores/authStore'
import { useUIStore } from '@/stores/uiStore'

let socket: Socket | null = null

export function getSocket(): Socket {
  if (!socket) {
    socket = io('/', {
      path: '/socket.io',
      auth: () => ({ token: useAuthStore.getState().accessToken }),
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    })

    socket.on('connect', () => {
      useUIStore.getState().setWsConnected(true)
    })

    socket.on('disconnect', (reason: string) => {
      useUIStore.getState().setWsConnected(false)
      // Transport closed by server — reconnection will be attempted automatically
      if (reason === 'io server disconnect') {
        socket?.connect()
      }
    })

    socket.on('connect_error', () => {
      useUIStore.getState().setWsConnected(false)
    })

    socket.on('reconnect', () => {
      useUIStore.getState().setWsConnected(true)
    })

    socket.on('reconnect_failed', () => {
      useUIStore.getState().setWsConnected(false)
    })
  }
  return socket
}

export function joinIncident(incidentId: string) {
  getSocket().emit('join:incident', { incident_id: incidentId })
}

export function leaveIncident(incidentId: string) {
  getSocket().emit('leave:incident', { incident_id: incidentId })
}

export function disconnectSocket() {
  if (socket) {
    socket.disconnect()
    socket = null
  }
}
