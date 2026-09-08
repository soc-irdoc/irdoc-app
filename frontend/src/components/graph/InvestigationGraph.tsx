/**
 * Investigation Graph — React Flow canvas for visualizing entity relationships.
 * Phase 4 component: lazy-loaded from IncidentWorkspacePage.
 */
import { useCallback, useRef, useState } from 'react'
import { toPng } from 'html-to-image'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  type Connection,
  type Edge,
  type Node,
  BackgroundVariant,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'

import { useGraph, useAddGraphEdge, useDeleteGraphEdge } from '@/hooks/useGraph'
import { useUIStore } from '@/stores/uiStore'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { EmptyState } from '@/components/common/EmptyState'
import { NODE_TYPES } from './NodeTypes'
import type { GraphNodeData } from '@/types/graph'

interface InvestigationGraphProps {
  incidentId: string
}

// ── Side Panel (node detail) ──────────────────────────────────────────────────

function NodeDetailPanel({
  node,
  onClose,
}: {
  node: Node
  onClose: () => void
}) {
  const d = node.data as unknown as GraphNodeData

  return (
    <div
      style={{
        position: 'absolute',
        top: 16,
        right: 16,
        width: 280,
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderRadius: 12,
        padding: 16,
        zIndex: 10,
        boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <h3 style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>
          Node Details
        </h3>
        <button className="icon-btn" onClick={onClose} aria-label="Close panel"><img src="/icons/multiply_color.svg" width={14} height={14} alt="" aria-hidden="true" /></button>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div>
          <p style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 2 }}>Label</p>
          <p style={{ fontSize: 12, color: 'var(--text-primary)', fontFamily: 'JetBrains Mono, monospace', wordBreak: 'break-all' }}>
            {d.label}
          </p>
        </div>

        {d.ioc_type && (
          <div>
            <p style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 2 }}>IOC Type</p>
            <p style={{ fontSize: 12, color: 'var(--text-primary)' }}>{d.ioc_type}</p>
          </div>
        )}

        {d.status && (
          <div>
            <p style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 2 }}>Status</p>
            <span className={`chip chip-${d.status === 'active' ? 'red' : d.status === 'blocked' ? 'yellow' : d.status === 'remediated' ? 'green' : 'muted'}`}>
              {d.status}
            </span>
          </div>
        )}

        {d.confidence !== undefined && (
          <div>
            <p style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 2 }}>Confidence</p>
            <p style={{ fontSize: 12, color: 'var(--text-primary)' }}>{d.confidence}%</p>
          </div>
        )}

        {d.entry_type && (
          <div>
            <p style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 2 }}>Entry Type</p>
            <p style={{ fontSize: 12, color: 'var(--text-primary)' }}>{d.entry_type}</p>
          </div>
        )}

        {d.occurred_at && (
          <div>
            <p style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 2 }}>Occurred At</p>
            <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>{new Date(d.occurred_at).toLocaleString()}</p>
          </div>
        )}

        {d.sha256 && (
          <div>
            <p style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 2 }}>SHA256</p>
            <p style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'JetBrains Mono, monospace' }}>{d.sha256}</p>
          </div>
        )}

        {/* Enrichment summary */}
        {d.enrichment && Object.keys(d.enrichment).length > 0 && (
          <div>
            <p style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>Enrichment</p>
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
              {Object.keys(d.enrichment)
                .filter((k) => !k.startsWith('_'))
                .map((k) => (
                  <span key={k} className="chip chip-muted" style={{ fontSize: 10 }}>{k}</span>
                ))}
            </div>
          </div>
        )}

        <button
          className="btn btn-ghost btn-sm"
          style={{ marginTop: 8 }}
          onClick={() => {
            if (d.label) navigator.clipboard.writeText(d.label)
          }}
        >
          Copy Value
        </button>
      </div>
    </div>
  )
}

// ── Main Component ────────────────────────────────────────────────────────────

export default function InvestigationGraph({ incidentId }: InvestigationGraphProps) {
  const addToast = useUIStore((s) => s.addToast)
  const { data: graphData, isLoading, refetch } = useGraph(incidentId)
  const addEdgeMutation = useAddGraphEdge(incidentId)
  const deleteEdgeMutation = useDeleteGraphEdge(incidentId)

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>((graphData?.nodes ?? []) as Node[])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>((graphData?.edges ?? []) as Edge[])
  const [selectedNode, setSelectedNode] = useState<Node | null>(null)
  const reactFlowRef = useRef<HTMLDivElement>(null)

  // Sync when data loads
  const prevDataRef = useRef<string>('')
  if (graphData) {
    const key = JSON.stringify({ nc: graphData.nodes.length, ec: graphData.edges.length })
    if (key !== prevDataRef.current) {
      prevDataRef.current = key
      setNodes(graphData.nodes as Node[])
      setEdges(graphData.edges as Edge[])
    }
  }

  const onConnect = useCallback(
    async (connection: Connection) => {
      if (!connection.source || !connection.target) return
      try {
        await addEdgeMutation.mutateAsync({
          source_node_id: connection.source,
          target_node_id: connection.target,
          label: 'related to',
        })
        setEdges((eds) => addEdge({ ...connection, animated: false, label: 'related to' }, eds))
        addToast('Relationship added', 'success')
      } catch {
        addToast('Failed to create relationship', 'error')
      }
    },
    [addEdgeMutation, setEdges, addToast]
  )

  async function handleDeleteEdge(edgeId: string) {
    if (!edgeId.startsWith('manual-')) {
      addToast('Only manually created edges can be deleted', 'info')
      return
    }
    try {
      await deleteEdgeMutation.mutateAsync(edgeId)
      setEdges((eds) => eds.filter((e) => e.id !== edgeId))
      addToast('Relationship removed', 'success')
    } catch {
      addToast('Failed to remove relationship', 'error')
    }
  }

  async function captureSnapshot(): Promise<string | null> {
    const el = reactFlowRef.current
    if (!el || nodes.length === 0) return null

    // html-to-image resolves getComputedStyle() before applying any style override,
    // so the only reliable way to inject light-mode values is to set them at :root
    // before the call and restore immediately after.
    const root = document.documentElement
    const lightVars: Record<string, string> = {
      '--bg-base':      '#ffffff',
      '--bg-surface':   '#f8fafc',
      '--bg-card':      '#ffffff',
      '--bg-elevated':  '#f1f5f9',
      '--border':       '#cbd5e1',
      '--text-primary': '#0f172a',
      '--text-secondary': '#334155',
      '--text-muted':   '#64748b',
    }
    for (const [k, v] of Object.entries(lightVars)) root.style.setProperty(k, v)

    try {
      return await toPng(el, {
        backgroundColor: '#ffffff',
        filter: (node) =>
          !(node instanceof HTMLElement) ||
          (!node.classList.contains('react-flow__controls') &&
           !node.classList.contains('react-flow__minimap') &&
           !node.classList.contains('react-flow__panel') &&
           !node.classList.contains('react-flow__background')),
        pixelRatio: 1.5,
      })
    } catch {
      return null
    } finally {
      for (const k of Object.keys(lightVars)) root.style.removeProperty(k)
    }
  }

  async function exportAsPNG() {
    const dataUrl = await captureSnapshot()
    if (!dataUrl) {
      addToast('Nothing to export', 'info')
      return
    }
    const link = document.createElement('a')
    link.download = `graph-${incidentId}.png`
    link.href = dataUrl
    link.click()
  }

  if (isLoading) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <LoadingSpinner />
      </div>
    )
  }

  if (!graphData || graphData.nodes.length === 0) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <EmptyState
          icon="link_color.svg"
          title="No graph data yet"
          description="Add IOCs and timeline entries to build the investigation graph."
        />
      </div>
    )
  }

  return (
    <div style={{ flex: 1, position: 'relative', background: 'var(--bg-base)' }} ref={reactFlowRef}>
      {/* Toolbar */}
      <div
        style={{
          position: 'absolute',
          top: 12,
          left: 12,
          zIndex: 10,
          display: 'flex',
          gap: 8,
          alignItems: 'center',
        }}
      >
        <div
          style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            borderRadius: 8,
            padding: '6px 12px',
            display: 'flex',
            gap: 8,
            alignItems: 'center',
          }}
        >
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            {nodes.length} nodes · {edges.length} edges
          </span>
          <button className="btn btn-ghost btn-sm" onClick={() => refetch()} style={{ fontSize: 11 }}>
            ↻ Refresh
          </button>
          <button className="btn btn-ghost btn-sm" onClick={exportAsPNG} style={{ fontSize: 11 }}>
            ↓ Export
          </button>
        </div>

        <div
          style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            borderRadius: 8,
            padding: '4px 10px',
            fontSize: 10,
            color: 'var(--text-muted)',
          }}
        >
          Drag between nodes to create relationships
        </div>
      </div>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={NODE_TYPES}
        onNodeClick={(_, node) => setSelectedNode((prev) => prev?.id === node.id ? null : node)}
        onEdgeDoubleClick={(_, edge) => handleDeleteEdge(edge.id)}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        colorMode="dark"
        style={{ background: 'var(--bg-base)' }}
        minZoom={0.1}
        maxZoom={3}
      >
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="var(--border)" />
        <Controls
          style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            borderRadius: 8,
          }}
        />
        <MiniMap
          nodeColor={(node) => {
            const d = node.data as unknown as GraphNodeData
            if (d.status) return '#ef4444'
            if (node.type === 'event') return 'var(--accent)'
            if (node.type === 'evidence') return '#8b5cf6'
            return '#6b7280'
          }}
          style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border)',
          }}
        />
      </ReactFlow>

      {/* Node detail side panel */}
      {selectedNode && (
        <NodeDetailPanel
          node={selectedNode}
          onClose={() => setSelectedNode(null)}
        />
      )}
    </div>
  )
}
