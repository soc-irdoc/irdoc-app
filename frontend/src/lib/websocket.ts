import { io, Socket } from 'socket.io-client'
import { useAuthStore } from '@/stores/authStore'

let socket: Socket | null = null

export function getSocket(): Socket {
  if (!socket) {
    socket = io('/', {
      path: '/socket.io',
      auth: () => ({ token: useAuthStore.getState().accessToken }),
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
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
