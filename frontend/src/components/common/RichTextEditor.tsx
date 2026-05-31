import { useEffect, useState } from 'react'
import { useEditor, EditorContent } from '@tiptap/react'
import { Extension } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import Underline from '@tiptap/extension-underline'
import { TextStyle } from '@tiptap/extension-text-style'
import Image from '@tiptap/extension-image'
import TaskList from '@tiptap/extension-task-list'
import TaskItem from '@tiptap/extension-task-item'
import Placeholder from '@tiptap/extension-placeholder'

// Tiptap initialises an empty editor as '<p></p>'. Normalise to '' so that
// the empty-string content prop doesn't trigger constant setContent calls.
function normalizeHtml(html: string): string {
  return html === '<p></p>' ? '' : html
}

// Extends the textStyle mark to carry font-size as a data attribute rather
// than an inline style, so bleach can whitelist it without a CSS sanitizer.
// CSS rules in global.css translate [data-font-size="Npx"] → font-size: N.
const FontSize = Extension.create({
  name: 'fontSize',
  addOptions() {
    return { types: ['textStyle'] }
  },
  addGlobalAttributes() {
    return [
      {
        types: this.options.types as string[],
        attributes: {
          fontSize: {
            default: null,
            parseHTML: (element) =>
              (element as HTMLElement).getAttribute('data-font-size') || null,
            renderHTML: (attributes) => {
              if (!attributes.fontSize) return {}
              return { 'data-font-size': attributes.fontSize }
            },
          },
        },
      },
    ]
  },
})

const FONT_SIZES = [
  '10px', '12px', '13px', '14px', '16px', '18px', '20px', '24px', '28px', '32px',
]

interface RichTextEditorProps {
  content: string
  onChange: (html: string) => void
  placeholder?: string
  enableTaskList?: boolean
  readOnly?: boolean
  // When true, external content syncs are skipped (prevents overwriting
  // in-progress edits when the parent re-renders after a successful save).
  isDirty?: boolean
}

export function RichTextEditor({
  content,
  onChange,
  placeholder = 'Start typing…',
  enableTaskList = false,
  readOnly = false,
  isDirty = false,
}: RichTextEditorProps) {
  // Force toolbar re-render on cursor/selection changes so active states update
  const [, forceUpdate] = useState({})
  const [editorHeight, setEditorHeight] = useState<number | null>(null)

  function handleResizeMouseDown(e: React.MouseEvent) {
    e.preventDefault()
    const startY = e.clientY
    const startHeight = (e.currentTarget.parentElement?.offsetHeight) ?? 180
    function onMove(ev: MouseEvent) {
      setEditorHeight(Math.max(180, startHeight + ev.clientY - startY))
    }
    function onUp() {
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
    }
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  }

  const editor = useEditor({
    extensions: [
      StarterKit,
      Underline,
      TextStyle,
      FontSize,
      Image.configure({ inline: false, allowBase64: true }),
      Placeholder.configure({ placeholder }),
      ...(enableTaskList
        ? [TaskList, TaskItem.configure({ nested: false })]
        : []),
    ],
    content,
    editable: !readOnly,
    onUpdate: ({ editor }) => {
      onChange(editor.getHTML())
    },
    editorProps: {
      // Intercept clipboard paste and handle image blobs as base64 inline images.
      handlePaste(view, event) {
        const items = Array.from(event.clipboardData?.items ?? [])
        const imageItem = items.find((item) => item.type.startsWith('image/'))
        if (!imageItem) return false
        const file = imageItem.getAsFile()
        if (!file) return false
        const reader = new FileReader()
        reader.onload = () => {
          const src = reader.result as string
          const imageNodeType = view.state.schema.nodes['image']
          if (!imageNodeType) return
          view.dispatch(
            view.state.tr.replaceSelectionWith(imageNodeType.create({ src }))
          )
        }
        reader.readAsDataURL(file)
        return true
      },
    },
  })

  useEffect(() => {
    if (!editor) return
    const handler = () => forceUpdate({})
    editor.on('transaction', handler)
    return () => {
      editor.off('transaction', handler)
    }
  }, [editor])

  // Sync external content changes into the editor. Skipped while the user has
  // unsaved edits (isDirty) to prevent a completed save from overwriting text
  // typed since the debounce fired.
  useEffect(() => {
    if (!editor || isDirty) return
    if (normalizeHtml(editor.getHTML()) !== (content ?? '')) {
      editor.commands.setContent(content ?? '', { emitUpdate: false })
    }
  }, [editor, content, isDirty])

  if (!editor) return null

  const isHeading1 = editor.isActive('heading', { level: 1 })
  const isHeading2 = editor.isActive('heading', { level: 2 })
  const headingValue = isHeading1 ? 'h1' : isHeading2 ? 'h2' : 'normal'

  // Bug 1 fix: no onMouseDown/e.preventDefault on <select> — that blocked the
  // dropdown from opening. Restore editor focus explicitly after the change.
  function setHeading(value: string) {
    if (value === 'h1') {
      editor.chain().toggleHeading({ level: 1 }).run()
    } else if (value === 'h2') {
      editor.chain().toggleHeading({ level: 2 }).run()
    } else {
      editor.chain().setParagraph().run()
    }
    editor.commands.focus()
  }

  const currentFontSize =
    (editor.getAttributes('textStyle').fontSize as string | null) ?? ''

  function setFontSize(value: string) {
    if (value) {
      editor.chain().setMark('textStyle', { fontSize: value }).run()
    } else {
      editor.chain().unsetMark('textStyle').run()
    }
    editor.commands.focus()
  }

  // Prevent the editor from losing focus (and the selection from being cleared)
  // when the user clicks a toolbar button. NOT applied to <select> elements —
  // e.preventDefault on a select's mousedown blocks the dropdown from opening.
  function blockBlur(e: React.MouseEvent) {
    e.preventDefault()
  }

  return (
    <div className="tiptap-editor">
      {!readOnly && (
        <div className="tiptap-toolbar">
          {enableTaskList ? (
            <button
              type="button"
              aria-label="Insert task item"
              className={`tb-btn tb-task-btn${editor.isActive('taskList') ? ' active' : ''}`}
              onMouseDown={blockBlur}
              onClick={() => editor.chain().toggleTaskList().run()}
              title="Insert task item"
            >
              ☑ Task
            </button>
          ) : (
            <select
              aria-label="Text style"
              className="tb-select"
              value={headingValue}
              onChange={(e) => setHeading(e.target.value)}
            >
              <option value="normal">Normal</option>
              <option value="h1">Heading 1</option>
              <option value="h2">Heading 2</option>
            </select>
          )}

          {/* Font size — visible on all toolbars */}
          <select
            aria-label="Font size"
            className="tb-select"
            value={currentFontSize}
            onChange={(e) => setFontSize(e.target.value)}
          >
            <option value="">Default</option>
            {FONT_SIZES.map((size) => (
              <option key={size} value={size}>
                {size.replace('px', '')}
              </option>
            ))}
          </select>

          <div className="tb-sep" />

          <button
            type="button"
            aria-label="Bold"
            className={`tb-btn${editor.isActive('bold') ? ' active' : ''}`}
            onMouseDown={blockBlur}
            onClick={() => editor.chain().toggleBold().run()}
            title="Bold"
          >
            <b>B</b>
          </button>
          <button
            type="button"
            aria-label="Italic"
            className={`tb-btn${editor.isActive('italic') ? ' active' : ''}`}
            onMouseDown={blockBlur}
            onClick={() => editor.chain().toggleItalic().run()}
            title="Italic"
          >
            <em>I</em>
          </button>
          <button
            type="button"
            aria-label="Underline"
            className={`tb-btn${editor.isActive('underline') ? ' active' : ''}`}
            onMouseDown={blockBlur}
            onClick={() => editor.chain().toggleUnderline().run()}
            title="Underline"
          >
            <u>U</u>
          </button>
          <button
            type="button"
            aria-label="Strikethrough"
            className={`tb-btn${editor.isActive('strike') ? ' active' : ''}`}
            onMouseDown={blockBlur}
            onClick={() => editor.chain().toggleStrike().run()}
            title="Strikethrough"
          >
            <s>S</s>
          </button>

          {!enableTaskList && (
            <>
              <div className="tb-sep" />
              <button
                type="button"
                aria-label="Bullet list"
                className={`tb-btn${editor.isActive('bulletList') ? ' active' : ''}`}
                onMouseDown={blockBlur}
                onClick={() => editor.chain().toggleBulletList().run()}
                title="Bullet list"
              >
                ≡
              </button>
              <button
                type="button"
                aria-label="Numbered list"
                className={`tb-btn${editor.isActive('orderedList') ? ' active' : ''}`}
                onMouseDown={blockBlur}
                onClick={() => editor.chain().toggleOrderedList().run()}
                title="Numbered list"
              >
                1≡
              </button>

              <div className="tb-sep" />

              <button
                type="button"
                aria-label="Indent"
                className="tb-btn"
                onMouseDown={blockBlur}
                onClick={() => editor.chain().sinkListItem('listItem').run()}
                title="Indent"
              >
                →
              </button>
              <button
                type="button"
                aria-label="Outdent"
                className="tb-btn"
                onMouseDown={blockBlur}
                onClick={() => editor.chain().liftListItem('listItem').run()}
                title="Outdent"
              >
                ←
              </button>
            </>
          )}
        </div>
      )}
      <div className="tiptap-body-wrap" style={editorHeight ? { height: editorHeight } : undefined}>
        <EditorContent editor={editor} className="tiptap-body" />
        {!readOnly && (
          <div className="resize-grip" onMouseDown={handleResizeMouseDown} />
        )}
      </div>
    </div>
  )
}
