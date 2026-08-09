import { forwardRef, useImperativeHandle, useRef, useState } from 'react'
import { Icon } from '../../shared/components/Icon'

export interface ComposerHandle {
  insert: (text: string) => void
  focus: () => void
}

interface ComposerProps {
  onSend: (text: string) => void
  busy: boolean
  disabled?: boolean
  placeholder?: string
}

/** Multiline message input. Enter sends, Shift+Enter adds a line break.
 *  While a request is in flight the send action is disabled, which also
 *  prevents duplicate submissions. */
export const Composer = forwardRef<ComposerHandle, ComposerProps>(function Composer(
  { onSend, busy, disabled = false, placeholder = 'Message the agent, or type / for a command' },
  ref,
) {
  const [text, setText] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useImperativeHandle(ref, () => ({
    insert(value: string) {
      setText(value)
      const textarea = textareaRef.current
      if (textarea) {
        textarea.focus()
        requestAnimationFrame(() => {
          textarea.setSelectionRange(value.length, value.length)
        })
      }
    },
    focus() {
      textareaRef.current?.focus()
    },
  }))

  function autosize() {
    const textarea = textareaRef.current
    if (!textarea) return
    textarea.style.height = 'auto'
    textarea.style.height = `${Math.min(textarea.scrollHeight, 160)}px`
  }

  function submit() {
    const value = text.trim()
    if (!value || busy || disabled) return
    onSend(value)
    setText('')
    requestAnimationFrame(autosize)
  }

  return (
    <div className="composer">
      <form
        className="composer__inner"
        onSubmit={(event) => {
          event.preventDefault()
          submit()
        }}
      >
        <label className="visually-hidden" htmlFor="composer-input">
          Message
        </label>
        <textarea
          id="composer-input"
          ref={textareaRef}
          className="composer__input"
          rows={1}
          value={text}
          placeholder={disabled ? 'This session has ended' : placeholder}
          disabled={disabled}
          onChange={(event) => {
            setText(event.target.value)
            autosize()
          }}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault()
              submit()
            }
          }}
        />
        <button
          type="submit"
          className="composer__send"
          disabled={busy || disabled || !text.trim()}
          aria-label={busy ? 'Sending…' : 'Send message'}
        >
          {busy ? <span className="spinner" aria-hidden="true" /> : <Icon name="send" size={18} />}
        </button>
      </form>
      <p className="composer__hint">
        <span>
          <kbd>Enter</kbd> to send · <kbd>Shift</kbd>+<kbd>Enter</kbd> for a new line
        </span>
        <span>
          <kbd>Ctrl</kbd>+<kbd>K</kbd> for commands
        </span>
      </p>
    </div>
  )
})
