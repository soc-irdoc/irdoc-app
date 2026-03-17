import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import apiClient from '@/lib/apiClient'
import type { Task, UpdateTaskPayload } from '@/types/task'
import type { ApiResponse } from '@/types/api'

export function useTasks(incidentId: string) {
  return useQuery({
    queryKey: ['tasks', incidentId],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<Task[]>>(`/incidents/${incidentId}/tasks`)
      return res.data.data
    },
    enabled: !!incidentId,
  })
}

export function useUpdateTask(incidentId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ taskId, payload }: { taskId: string; payload: UpdateTaskPayload }) => {
      const res = await apiClient.put<ApiResponse<Task>>(
        `/incidents/${incidentId}/tasks/${taskId}`,
        payload
      )
      return res.data.data
    },
    onMutate: async ({ taskId, payload }) => {
      // Optimistic update
      await qc.cancelQueries({ queryKey: ['tasks', incidentId] })
      const previous = qc.getQueryData<Task[]>(['tasks', incidentId])
      qc.setQueryData<Task[]>(['tasks', incidentId], (old) =>
        old?.map((t) => (t.id === taskId ? { ...t, ...payload } : t)) ?? []
      )
      return { previous }
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.previous) {
        qc.setQueryData(['tasks', incidentId], ctx.previous)
      }
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['tasks', incidentId] })
    },
  })
}
