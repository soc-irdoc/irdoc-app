import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import apiClient from '@/lib/apiClient'
import type { Asset, AssetLink } from '@/types/asset'
import type { ApiResponse } from '@/types/api'

// ── Asset CRUD ────────────────────────────────────────────────────────────────

export function useAssets(incidentId: string) {
  return useQuery({
    queryKey: ['assets', incidentId],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<Asset[]>>(`/incidents/${incidentId}/assets`)
      return res.data.data
    },
    enabled: !!incidentId,
  })
}

export function useCreateAsset(incidentId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      const res = await apiClient.post<ApiResponse<Asset>>(
        `/incidents/${incidentId}/assets`,
        payload
      )
      return res.data.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['assets', incidentId] })
      qc.invalidateQueries({ queryKey: ['graph', incidentId] })
    },
  })
}

export function useBulkCreateAssets(incidentId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      const res = await apiClient.post<ApiResponse<Asset[]>>(
        `/incidents/${incidentId}/assets/bulk`,
        payload
      )
      return res.data.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['assets', incidentId] })
      qc.invalidateQueries({ queryKey: ['graph', incidentId] })
    },
  })
}

export function useUpdateAsset(incidentId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ assetId, payload }: { assetId: string; payload: Record<string, unknown> }) => {
      const res = await apiClient.put<ApiResponse<Asset>>(
        `/incidents/${incidentId}/assets/${assetId}`,
        payload
      )
      return res.data.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['assets', incidentId] })
      qc.invalidateQueries({ queryKey: ['graph', incidentId] })
    },
  })
}

export function useDeleteAsset(incidentId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (assetId: string) => {
      await apiClient.delete(`/incidents/${incidentId}/assets/${assetId}`)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['assets', incidentId] })
      qc.invalidateQueries({ queryKey: ['graph', incidentId] })
    },
  })
}

// ── Asset-to-asset links ──────────────────────────────────────────────────────

export function useAssetLinks(incidentId: string) {
  return useQuery({
    queryKey: ['asset-links', incidentId],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<AssetLink[]>>(
        `/incidents/${incidentId}/asset-links`
      )
      return res.data.data
    },
    enabled: !!incidentId,
  })
}

export function useCreateAssetLink(incidentId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (payload: {
      source_id: string
      target_id: string
      link_type: string
      label?: string
    }) => {
      const res = await apiClient.post<ApiResponse<AssetLink>>(
        `/incidents/${incidentId}/asset-links`,
        payload
      )
      return res.data.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['asset-links', incidentId] })
      qc.invalidateQueries({ queryKey: ['graph', incidentId] })
    },
  })
}

export function useDeleteAssetLink(incidentId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (linkId: string) => {
      await apiClient.delete(`/incidents/${incidentId}/asset-links/${linkId}`)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['asset-links', incidentId] })
      qc.invalidateQueries({ queryKey: ['graph', incidentId] })
    },
  })
}

// ── Asset-timeline links ──────────────────────────────────────────────────────

export function useLinkAssetsToEntry(incidentId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (payload: { asset_ids: string[]; timeline_entry_id: string }) => {
      const res = await apiClient.post(
        `/incidents/${incidentId}/assets/timeline-links`,
        payload
      )
      return res.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['assets', incidentId] })
      qc.invalidateQueries({ queryKey: ['graph', incidentId] })
    },
  })
}

export function useEntryAssets(incidentId: string, entryId: string) {
  return useQuery({
    queryKey: ['entry-assets', incidentId, entryId],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<Asset[]>>(
        `/incidents/${incidentId}/timeline/${entryId}/assets`
      )
      return res.data.data
    },
    enabled: !!incidentId && !!entryId,
  })
}
