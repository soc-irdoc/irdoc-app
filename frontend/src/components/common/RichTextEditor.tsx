import { useEffect, useState } from 'react'
import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Underline from '@tiptap/extension-underline'
import TaskList from '@tiptap/extension-task-list'
import TaskItem from '@tiptap/extension-task-item'
import Placeholder from '@tiptap/extension-placeholder'

// Tiptap initialises an empty editor as '<p></p>'. Normalise to '' so that
// the empty-string content prop doesn't trigger constant setContent calls.
function normalizeHtml(html: string): string {
  return html === '<p></p>' ? '' : html
}

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

  const editor = useEditor({
    extensions: [
      StarterKit,
      Underline,
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

  function setHeading(value: string) {
    if (value === 'h1') {
      editor.chain().focus().toggleHeading({ level: 1 }).run()
    } else if (value === 'h2') {
      editor.chain().focus().toggleHeading({ level: 2 }).run()
    } else {
      editor.chain().focus().setParagraph().run()
    }
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
              onClick={() => editor.chain().focus().toggleTaskList().run()}
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

          <div className="tb-sep" />

          <button
            type="button"
            aria-label="Bold"
            className={`tb-btn${editor.isActive('bold') ? ' active' : ''}`}
            onClick={() => editor.chain().focus().toggleBold().run()}
            title="Bold"
          >
            <b>B</b>
          </button>
          <button
            type="button"
            aria-label="Italic"
            className={`tb-btn${editor.isActive('italic') ? ' active' : ''}`}
            onClick={() => editor.chain().focus().toggleItalic().run()}
            title="Italic"
          >
            <em>I</em>
          </button>
          <button
            type="button"
            aria-label="Underline"
            className={`tb-btn${editor.isActive('underline') ? ' active' : ''}`}
            onClick={() => editor.chain().focus().toggleUnderline().run()}
            title="Underline"
          >
            <u>U</u>
          </button>
          <button
            type="button"
            aria-label="Strikethrough"
            className={`tb-btn${editor.isActive('strike') ? ' active' : ''}`}
            onClick={() => editor.chain().focus().toggleStrike().run()}
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
                onClick={() => editor.chain().focus().toggleBulletList().run()}
                title="Bullet list"
              >
                ≡
              </button>
              <button
                type="button"
                aria-label="Numbered list"
                className={`tb-btn${editor.isActive('orderedList') ? ' active' : ''}`}
                onClick={() => editor.chain().focus().toggleOrderedList().run()}
                title="Numbered list"
              >
                1≡
              </button>

              <div className="tb-sep" />

              <button
                type="button"
                aria-label="Indent"
                className="tb-btn"
                onClick={() => editor.chain().focus().sinkListItem('listItem').run()}
                title="Indent"
              >
                →
              </button>
              <button
                type="button"
                aria-label="Outdent"
                className="tb-btn"
                onClick={() => editor.chain().focus().liftListItem('listItem').run()}
                title="Outdent"
              >
                ←
              </button>
            </>
          )}
        </div>
      )}
      <EditorContent editor={editor} className="tiptap-body" />
    </div>
  )
}
