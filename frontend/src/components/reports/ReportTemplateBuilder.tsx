/**
 * Report Template Builder — drag-and-drop canvas + block library.
 *
 * Left side: canvas (ordered list of blocks, drag to reorder, click to configure)
 * Right side: block library (click or drag to add)
 *
 * Uses @dnd-kit/core for drag-and-drop.
 */
import { useState, useCallback } from 'react'
import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
} from '@dnd-kit/core'
import {
  SortableContext,
  arrayMove,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import BlockConfigPanel from './BlockConfigPanel'
import { ReportBlock, BlockType, BLOCK_LIBRARY } from '@/types/report'

interface Props {
  blocks: ReportBlock[]
  onChange: (blocks: ReportBlock[]) => void
  incidentId?: string
  onPreview?: () => void
}

let _idCounter = 1
function newId() {
  return `blk-${Date.now()}-${_idCounter++}`
}

// ─── Sortable Block Card ───────────────────────────────────────────────────────

function SortableBlockCard({
  block,
  isSelected,
  onSelect,
  onRemove,
  onChange,
}: {
  block: ReportBlock
  isSelected: boolean
  onSelect: () => void
  onRemove: () => void
  onChange: (updates: Partial<ReportBlock>) => void
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: block.id })

  const libEntry = BLOCK_LIBRARY.find((b) => b.type === block.type)

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  }

  return (
    <div ref={setNodeRef} style={style}>
      <div
        style={{
          background: isSelected ? 'var(--accent-dim)' : 'var(--bg-surface)',
          border: `1px solid ${isSelected ? 'var(--accent)' : 'var(--border)'}`,
          borderRadius: '8px',
          overflow: 'hidden',
          transition: 'border-color 0.15s',
        }}
      >
        {/* Block header row */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            padding: '10px 12px',
            cursor: 'pointer',
          }}
          onClick={onSelect}
        >
          {/* Drag handle */}
          <div
            {...attributes}
            {...listeners}
            style={{
              cursor: 'grab',
              color: 'var(--text-muted)',
              marginRight: '10px',
              fontSize: '14px',
              lineHeight: 1,
              padding: '2px 4px',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            ≡
          </div>

          {libEntry?.icon && (libEntry.icon.endsWith('.svg')
            ? <img src={`/icons/${libEntry.icon}`} width={16} height={16} alt="" aria-hidden="true" style={{ marginRight: '8px', flexShrink: 0 }} />
            : <span style={{ fontSize: '14px', marginRight: '8px', flexShrink: 0, lineHeight: 1 }}>{libEntry.icon}</span>
          )}

          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
              {libEntry?.label ?? block.type}
            </div>
            {(block.label || block.filter || block.field) && (
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '1px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {block.label ? block.label : block.field ? `→ ${block.field}` : block.filter ?? ''}
              </div>
            )}
          </div>

          <button
            className="icon-btn"
            style={{ color: 'var(--text-muted)', marginLeft: '6px', flexShrink: 0 }}
            onClick={(e) => { e.stopPropagation(); onRemove() }}
            aria-label="Remove block"
          >
            <img src="/icons/multiply_color.svg" width={12} height={12} alt="" aria-hidden="true" />
          </button>
        </div>

        {/* Inline config panel */}
        {isSelected && (
          <div
            style={{
              padding: '12px 16px 14px',
              borderTop: '1px solid var(--border)',
              background: 'var(--bg-base)',
            }}
          >
            <BlockConfigPanel block={block} onChange={onChange} />
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Block Library Panel ───────────────────────────────────────────────────────

function BlockLibraryItem({
  icon,
  label,
  description,
  onAdd,
}: {
  icon: string
  label: string
  description: string
  onAdd: () => void
}) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        padding: '8px 10px',
        borderRadius: '6px',
        cursor: 'pointer',
        transition: 'background 0.12s',
      }}
      onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = 'var(--bg-surface)' }}
      onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = 'transparent' }}
      onClick={onAdd}
      title={description}
    >
      {icon.endsWith('.svg')
        ? <img src={`/icons/${icon}`} width={16} height={16} alt="" aria-hidden="true" style={{ flexShrink: 0 }} />
        : <span style={{ fontSize: '14px', width: '22px', textAlign: 'center', flexShrink: 0, lineHeight: 1 }}>{icon}</span>
      }
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>
          {label}
        </div>
      </div>
      <button
        className="btn btn-ghost btn-sm"
        style={{ fontSize: '11px', padding: '2px 7px', flexShrink: 0 }}
        onClick={(e) => { e.stopPropagation(); onAdd() }}
      >
        + Add
      </button>
    </div>
  )
}

// ─── Main Builder Component ────────────────────────────────────────────────────

export default function ReportTemplateBuilder({ blocks, onChange, onPreview }: Props) {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [activeDragId, setActiveDragId] = useState<string | null>(null)

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  )

  const addBlock = useCallback((type: BlockType) => {
    const libEntry = BLOCK_LIBRARY.find((b) => b.type === type)
    const newBlock: ReportBlock = {
      id: newId(),
      type,
      ...libEntry?.defaultConfig,
    }
    onChange([...blocks, newBlock])
    setSelectedId(newBlock.id)
  }, [blocks, onChange])

  const removeBlock = useCallback((id: string) => {
    onChange(blocks.filter((b) => b.id !== id))
    if (selectedId === id) setSelectedId(null)
  }, [blocks, onChange, selectedId])

  const updateBlock = useCallback((id: string, updates: Partial<ReportBlock>) => {
    onChange(blocks.map((b) => b.id === id ? { ...b, ...updates } : b))
  }, [blocks, onChange])

  const handleDragStart = (event: DragStartEvent) => {
    setActiveDragId(event.active.id as string)
  }

  const handleDragEnd = (event: DragEndEvent) => {
    setActiveDragId(null)
    const { active, over } = event
    if (over && active.id !== over.id) {
      const oldIdx = blocks.findIndex((b) => b.id === active.id)
      const newIdx = blocks.findIndex((b) => b.id === over.id)
      onChange(arrayMove(blocks, oldIdx, newIdx))
    }
  }

  const activeBlock = activeDragId ? blocks.find((b) => b.id === activeDragId) : null

  return (
    <div style={{ display: 'flex', gap: '0', height: '100%', minHeight: '500px' }}>
      {/* ── Canvas ── */}
      <div style={{ flex: 1, padding: '16px 20px', overflowY: 'auto', borderRight: '1px solid var(--border)' }}>
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <SortableContext items={blocks.map((b) => b.id)} strategy={verticalListSortingStrategy}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {blocks.length === 0 && (
                <div
                  style={{
                    border: '1px dashed var(--border)',
                    borderRadius: '8px',
                    padding: '32px',
                    textAlign: 'center',
                    color: 'var(--text-muted)',
                    fontSize: '13px',
                  }}
                >
                  Add blocks from the panel on the right →
                </div>
              )}
              {blocks.map((block) => (
                <SortableBlockCard
                  key={block.id}
                  block={block}
                  isSelected={selectedId === block.id}
                  onSelect={() => setSelectedId(selectedId === block.id ? null : block.id)}
                  onRemove={() => removeBlock(block.id)}
                  onChange={(updates) => updateBlock(block.id, updates)}
                />
              ))}
            </div>
          </SortableContext>

          <DragOverlay>
            {activeBlock && (
              <div
                style={{
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--accent)',
                  borderRadius: '8px',
                  padding: '10px 12px',
                  boxShadow: '0 8px 24px rgba(0,0,0,0.3)',
                  fontSize: '13px',
                  color: 'var(--text-primary)',
                }}
              >
                {(() => { const e = BLOCK_LIBRARY.find((b) => b.type === activeBlock.type); if (!e) return null; return <>{e.icon.endsWith('.svg') ? <img src={`/icons/${e.icon}`} width={14} height={14} alt="" aria-hidden="true" style={{ display: 'inline-block', verticalAlign: 'middle', marginRight: 6, flexShrink: 0 }} /> : <span style={{ marginRight: 6 }}>{e.icon}</span>}{e.label}</> })()}
              </div>
            )}
          </DragOverlay>
        </DndContext>

        {/* Canvas footer actions */}
        {blocks.length > 0 && (
          <div style={{ marginTop: '16px', display: 'flex', gap: '8px' }}>
            {onPreview && (
              <button className="btn btn-ghost btn-sm" onClick={onPreview}>
                <img src="/icons/eyes_color.svg" width={16} height={16} alt="" aria-hidden="true" style={{ verticalAlign: 'middle', marginRight: 4 }} />Preview
              </button>
            )}
          </div>
        )}
      </div>

      {/* ── Block Library ── */}
      <div style={{ width: '220px', flexShrink: 0, padding: '16px 12px', overflowY: 'auto' }}>
        <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '10px', padding: '0 4px' }}>
          Available Blocks
        </div>
        {BLOCK_LIBRARY.map((entry) => (
          <BlockLibraryItem
            key={entry.type}
            {...entry}
            onAdd={() => addBlock(entry.type)}
          />
        ))}
      </div>
    </div>
  )
}
