import { useState } from 'react'
import { ConfirmDialog } from '../../shared/components/ConfirmDialog'
import { Icon } from '../../shared/components/Icon'
import type { OperationOutcome } from '../../app/store'

interface MemoryViewProps {
  memory: Record<string, string>
  disabled: boolean
  onAdd: (information: string) => Promise<OperationOutcome>
  onDelete: (key: string) => Promise<OperationOutcome>
  onClearAll: () => Promise<OperationOutcome>
}

export function MemoryView({ memory, disabled, onAdd, onDelete, onClearAll }: MemoryViewProps) {
  const [draft, setDraft] = useState('')
  const [statusMessage, setStatusMessage] = useState<{ ok: boolean; text: string } | null>(null)
  const [busy, setBusy] = useState(false)
  const [confirmingClear, setConfirmingClear] = useState(false)
  const entries = Object.entries(memory)

  async function run(action: () => Promise<OperationOutcome>) {
    setBusy(true)
    const outcome = await action()
    setStatusMessage({ ok: outcome.ok, text: outcome.message })
    setBusy(false)
    return outcome
  }

  async function submitAdd(event: React.FormEvent) {
    event.preventDefault()
    const information = draft.trim()
    if (!information) {
      setStatusMessage({ ok: false, text: 'Enter something to remember first.' })
      return
    }
    const outcome = await run(() => onAdd(information))
    if (outcome.ok) setDraft('')
  }

  return (
    <section className="panel" aria-label="Memory">
      <div className="panel__inner">
        <div className="panel__header">
          <div>
            <h2 className="panel__title">Memory</h2>
            <p className="panel__desc">
              Saved information persists between sessions in <code>data/memory.json</code> on this
              computer. Nothing is sent anywhere else — you can remove any entry, or everything, at
              any time.
            </p>
          </div>
          {entries.length > 0 ? (
            <button
              type="button"
              className="btn btn--ghost"
              onClick={() => setConfirmingClear(true)}
              disabled={busy || disabled}
            >
              <Icon name="trash" size={16} />
              Clear all
            </button>
          ) : null}
        </div>

        <form className="memory__form" onSubmit={submitAdd}>
          <label className="visually-hidden" htmlFor="memory-input">
            Information to remember
          </label>
          <input
            id="memory-input"
            className="field__input"
            type="text"
            placeholder="e.g. My preferred language is English"
            value={draft}
            maxLength={4000}
            onChange={(event) => setDraft(event.target.value)}
            disabled={busy || disabled}
          />
          <button type="submit" className="btn btn--primary" disabled={busy || disabled}>
            {busy ? <span className="spinner" aria-hidden="true" /> : <Icon name="plus" size={16} />}
            Remember
          </button>
        </form>

        <p
          className={`statusline ${
            statusMessage ? (statusMessage.ok ? 'statusline--success' : 'statusline--error') : ''
          }`}
          role="status"
          aria-live="polite"
        >
          {statusMessage?.text ?? ''}
        </p>

        {entries.length === 0 ? (
          <div className="empty">
            <div className="empty__icon">
              <Icon name="memory" size={32} />
            </div>
            <p>Nothing saved yet. Anything you remember here will be available next session.</p>
          </div>
        ) : (
          <ul className="memory__list">
            {entries.map(([key, value]) => (
              <li key={key} className="memory__item">
                <span className="memory__key">{key}</span>
                <span className="memory__text">{value}</span>
                <button
                  type="button"
                  className="iconbtn"
                  aria-label={`Forget ${key}`}
                  onClick={() => void run(() => onDelete(key))}
                  disabled={busy || disabled}
                >
                  <Icon name="trash" size={16} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {confirmingClear ? (
        <ConfirmDialog
          title="Clear all memory?"
          message="Every saved entry will be permanently removed from data/memory.json. This cannot be undone."
          confirmLabel="Clear all memory"
          busy={busy}
          onCancel={() => setConfirmingClear(false)}
          onConfirm={() => {
            void run(onClearAll).then(() => setConfirmingClear(false))
          }}
        />
      ) : null}
    </section>
  )
}
