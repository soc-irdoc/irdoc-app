import { useEffect, useRef, useState } from 'react'
import { fileSize } from '@/lib/utils'

interface AttachmentZoneProps {
  files: File[]
  onFilesChange: (files: File[]) => void
}

export function AttachmentZone({ files, onFilesChange }: AttachmentZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragOver, setDragOver] = useState(false)

  // Global paste listener — captures screenshots pasted anywhere
  useEffect(() => {
    const handlePaste = (e: ClipboardEvent) => {
      const items = Array.from(e.clipboardData?.items ?? [])
      items.forEach((item) => {
        if (item.type.startsWith('image/')) {
          const file = item.getAsFile()
          if (file) onFilesChange([...files, file])
        }
      })
    }
    document.addEventListener('paste', handlePaste)
    return () => document.removeEventListener('paste', handlePaste)
  }, [files, onFilesChange])

  function addFiles(newFiles: FileList | null) {
    if (!newFiles) return
    onFilesChange([...files, ...Array.from(newFiles)])
  }

  function removeFile(idx: number) {
    onFilesChange(files.filter((_, i) => i !== idx))
  }

  return (
    <div>
      <div
        className={`attach-zone${dragOver ? ' drag-over' : ''}`}
        style={{
          border: `1px dashed ${dragOver ? 'var(--accent)' : 'var(--border)'}`,
          borderRadius: 8,
          padding: 16,
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          cursor: 'pointer',
          transition: 'all 0.15s',
          color: dragOver ? 'var(--accent)' : 'var(--text-muted)',
          background: dragOver ? 'var(--accent-dim)' : 'transparent',
          fontSize: 13,
        }}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragOver(false)
          addFiles(e.dataTransfer.files)
        }}
      >
        <img src="/icons/paperclip_color.svg" width={22} height={22} alt="" aria-hidden="true" />
        <div>
          <p>Drop files here, click to browse, or paste a screenshot</p>
          <p style={{ fontSize: 11, marginTop: 2, color: 'var(--text-muted)' }}>
            Max 50MB per file
          </p>
        </div>
      </div>

      <input
        ref={inputRef}
        type="file"
        multiple
        style={{ display: 'none' }}
        onChange={(e) => addFiles(e.target.files)}
      />

      {files.length > 0 && (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 10 }}>
          {files.map((file, idx) => (
            <div
              key={idx}
              style={{
                width: 64,
                height: 64,
                borderRadius: 8,
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border)',
                overflow: 'hidden',
                position: 'relative',
                cursor: 'default',
              }}
            >
              {file.type.startsWith('image/') ? (
                <img
                  src={URL.createObjectURL(file)}
                  alt={file.name}
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                />
              ) : (
                <div
                  style={{
                    width: '100%',
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 2,
                    padding: 4,
                  }}
                >
                  <img src="/icons/page_facing_up_color.svg" width={20} height={20} alt="" aria-hidden="true" />
                  <span style={{ fontSize: 9, color: 'var(--text-muted)', textAlign: 'center', wordBreak: 'break-all' }}>
                    {fileSize(file.size)}
                  </span>
                </div>
              )}
              <button
                onClick={() => removeFile(idx)}
                aria-label="Remove attachment"
                style={{
                  position: 'absolute',
                  top: 2,
                  right: 2,
                  background: 'rgba(0,0,0,0.7)',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '50%',
                  width: 16,
                  height: 16,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: 0,
                }}
              >
                <img src="/icons/multiply_color.svg" width={14} height={14} alt="" aria-hidden="true" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
