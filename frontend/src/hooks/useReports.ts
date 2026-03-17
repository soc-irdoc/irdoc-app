import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import apiClient from '@/lib/apiClient'
import { Report, ReportGenerateRequest } from '@/types/report'
import { useUIStore } from '@/stores/uiStore'

export function useReports(incidentId: string) {
  return useQuery<Report[]>({
    queryKey: ['reports', incidentId],
    queryFn: async () => {
      const { data } = await apiClient.get(`/incidents/${incidentId}/reports`)
      return data.data
    },
    enabled: !!incidentId,
    refetchInterval: (query) => {
      // Poll every 3s while any report is pending/generating
      const reports = query.state.data
      if (reports?.some((r: Report) => r.status === 'pending' || r.status === 'generating')) {
        return 3000
      }
      return false
    },
  })
}

export function useGenerateReport(incidentId: string) {
  const qc = useQueryClient()
  const addToast = useUIStore((s) => s.addToast)

  return useMutation({
    mutationFn: async (request: ReportGenerateRequest) => {
      const { data } = await apiClient.post(`/incidents/${incidentId}/reports`, request)
      return data.data as Report
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['reports', incidentId] })
      addToast('Report generation started…', 'info')
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail || 'Failed to start report generation'
      addToast(msg, 'error')
    },
  })
}

export function useDeleteReport(incidentId: string) {
  const qc = useQueryClient()
  const addToast = useUIStore((s) => s.addToast)

  return useMutation({
    mutationFn: async (reportId: string) => {
      await apiClient.delete(`/reports/${reportId}`)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['reports', incidentId] })
      addToast('Report deleted', 'success')
    },
  })
}

export function useDownloadReport() {
  const addToast = useUIStore((s) => s.addToast)

  return useMutation({
    mutationFn: async ({ reportId, filename }: { reportId: string; filename: string }) => {
      const response = await apiClient.get(`/reports/${reportId}/download`, {
        responseType: 'blob',
      })
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', filename)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    },
    onError: () => {
      addToast('Download failed', 'error')
    },
  })
}
