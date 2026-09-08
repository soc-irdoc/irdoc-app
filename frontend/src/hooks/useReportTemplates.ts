import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import apiClient from '@/lib/apiClient'
import { ReportTemplate } from '@/types/report'
import { useUIStore } from '@/stores/uiStore'
import { getErrorMessage } from '@/lib/utils'

export function useUploadTemplateLogo(templateId: string) {
  const qc = useQueryClient()
  const addToast = useUIStore((s) => s.addToast)

  return useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData()
      form.append('file', file)
      const { data } = await apiClient.post(`/report-templates/${templateId}/logo`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return data.data as ReportTemplate
    },
    onSuccess: (t) => {
      qc.invalidateQueries({ queryKey: ['report-templates'] })
      qc.setQueryData(['report-template', templateId], t)
      addToast('Logo uploaded', 'success')
    },
    onError: (err) => {
      addToast(getErrorMessage(err, 'Failed to upload logo'), 'error')
    },
  })
}

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
    onError: (err) => {
      addToast(getErrorMessage(err, 'Failed to create template'), 'error')
    },
  })
}

export function useUpdateReportTemplate(templateId: string) {
  const qc = useQueryClient()
  const addToast = useUIStore((s) => s.addToast)

  return useMutation({
    mutationFn: async (payload: { name?: string; destination?: string; description?: string; schema_json?: object[]; primary_colour?: string; company_name?: string }) => {
      const { data } = await apiClient.put(`/report-templates/${templateId}`, payload)
      return data.data as ReportTemplate
    },
    onSuccess: (t) => {
      qc.invalidateQueries({ queryKey: ['report-templates'] })
      qc.invalidateQueries({ queryKey: ['report-template', templateId] })
      addToast(`Template "${t.name}" saved`, 'success')
    },
    onError: (err) => {
      addToast(getErrorMessage(err, 'Failed to save template'), 'error')
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

export function useToggleAiAutoGenerate() {
  const qc = useQueryClient()
  const addToast = useUIStore((s) => s.addToast)

  return useMutation({
    mutationFn: async ({ templateId, enabled }: { templateId: string; enabled: boolean }) => {
      const { data } = await apiClient.put(`/report-templates/${templateId}`, { ai_auto_generate: enabled })
      return data.data as ReportTemplate
    },
    onSuccess: (t) => {
      qc.invalidateQueries({ queryKey: ['report-templates'] })
      addToast(
        t.ai_auto_generate
          ? `AI auto-generate enabled for "${t.name}"`
          : `AI auto-generate disabled for "${t.name}"`,
        'success',
      )
    },
    onError: (err) => {
      addToast(getErrorMessage(err, 'Failed to update template'), 'error')
    },
  })
}

export function useToggleHideReportTemplate() {
  const qc = useQueryClient()
  const addToast = useUIStore((s) => s.addToast)

  return useMutation({
    mutationFn: async ({ templateId, hidden }: { templateId: string; hidden: boolean }) => {
      const { data } = await apiClient.put(`/report-templates/${templateId}`, { is_hidden: hidden })
      return data.data as ReportTemplate
    },
    onSuccess: (t) => {
      qc.invalidateQueries({ queryKey: ['report-templates'] })
      addToast(t.is_hidden ? `"${t.name}" hidden from Reports tab` : `"${t.name}" restored`, 'success')
    },
    onError: (err) => {
      addToast(getErrorMessage(err, 'Failed to update template'), 'error')
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
    onError: (err) => {
      addToast(getErrorMessage(err, 'Failed to clone template'), 'error')
    },
  })
}
