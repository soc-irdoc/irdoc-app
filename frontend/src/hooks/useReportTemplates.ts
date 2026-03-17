import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import apiClient from '@/lib/apiClient'
import { ReportTemplate } from '@/types/report'
import { useUIStore } from '@/stores/uiStore'

export function useReportTemplates() {
  return useQuery<ReportTemplate[]>({
    queryKey: ['report-templates'],
    queryFn: async () => {
      const { data } = await apiClient.get('/report-templates')
      return data
    },
    staleTime: 60_000,
  })
}

export function useReportTemplate(templateId: string | null) {
  return useQuery<ReportTemplate>({
    queryKey: ['report-template', templateId],
    queryFn: async () => {
      const { data } = await apiClient.get(`/report-templates/${templateId}`)
      return data
    },
    enabled: !!templateId,
  })
}

export function useCreateReportTemplate() {
  const qc = useQueryClient()
  const addToast = useUIStore((s) => s.addToast)

  return useMutation({
    mutationFn: async (payload: { name: string; destination: string; description?: string; schema_json: object[] }) => {
      const { data } = await apiClient.post('/report-templates', payload)
      return data.data as ReportTemplate
    },
    onSuccess: (t) => {
      qc.invalidateQueries({ queryKey: ['report-templates'] })
      addToast(`Template "${t.name}" created`, 'success')
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail || 'Failed to create template'
      addToast(msg, 'error')
    },
  })
}

export function useUpdateReportTemplate(templateId: string) {
  const qc = useQueryClient()
  const addToast = useUIStore((s) => s.addToast)

  return useMutation({
    mutationFn: async (payload: { name?: string; destination?: string; description?: string; schema_json?: object[] }) => {
      const { data } = await apiClient.put(`/report-templates/${templateId}`, payload)
      return data.data as ReportTemplate
    },
    onSuccess: (t) => {
      qc.invalidateQueries({ queryKey: ['report-templates'] })
      qc.invalidateQueries({ queryKey: ['report-template', templateId] })
      addToast(`Template "${t.name}" saved`, 'success')
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail || 'Failed to save template'
      addToast(msg, 'error')
    },
  })
}

export function useDeleteReportTemplate() {
  const qc = useQueryClient()
  const addToast = useUIStore((s) => s.addToast)

  return useMutation({
    mutationFn: async (templateId: string) => {
      await apiClient.delete(`/report-templates/${templateId}`)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['report-templates'] })
      addToast('Template deleted', 'success')
    },
  })
}

export function useCloneReportTemplate() {
  const qc = useQueryClient()
  const addToast = useUIStore((s) => s.addToast)

  return useMutation({
    mutationFn: async (templateId: string) => {
      const { data } = await apiClient.post(`/report-templates/${templateId}/clone`)
      return data.data as ReportTemplate
    },
    onSuccess: (t) => {
      qc.invalidateQueries({ queryKey: ['report-templates'] })
      addToast(`"${t.name}" created — ready to edit`, 'success')
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail || 'Failed to clone template'
      addToast(msg, 'error')
    },
  })
}
