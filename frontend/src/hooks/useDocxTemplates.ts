import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import apiClient from '@/lib/apiClient'
import type { DocxTemplate } from '@/types/docxTemplate'

const QK = 'docx-templates'

export function useDocxTemplates() {
  return useQuery<DocxTemplate[]>({
    queryKey: [QK],
    queryFn: async () => {
      const res = await apiClient.get('/pdf-templates')
      return res.data.data ?? []
    },
    staleTime: 30_000,
  })
}

export function useDownloadBaseTemplate() {
  return useMutation({
    mutationFn: async () => {
      const res = await apiClient.get('/pdf-templates/base', { responseType: 'blob' })
      const url = URL.createObjectURL(new Blob([res.data]))
      const a = document.createElement('a')
      a.href = url
      a.download = 'irdoc_base_template.docx'
      a.click()
      URL.revokeObjectURL(url)
    },
  })
}

export function useUploadDocxTemplate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ name, file }: { name: string; file: File }) => {
      const fd = new FormData()
      fd.append('name', name)
      fd.append('file', file)
      const res = await apiClient.post('/pdf-templates', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return res.data.data as DocxTemplate
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: [QK] }),
  })
}

export function useSetDefaultDocxTemplate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (templateId: string) => {
      await apiClient.post(`/pdf-templates/${templateId}/set-default`)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: [QK] }),
  })
}

export function useRenameDocxTemplate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, name }: { id: string; name: string }) => {
      await apiClient.patch(`/pdf-templates/${id}`, { name })
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: [QK] }),
  })
}

export function useDeleteDocxTemplate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (templateId: string) => {
      await apiClient.delete(`/pdf-templates/${templateId}`)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: [QK] }),
  })
}
