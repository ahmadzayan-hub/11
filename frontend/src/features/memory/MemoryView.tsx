import { useMemo, useState } from 'react'
import { ConfirmDialog } from '../../shared/components/ConfirmDialog'
import { Icon } from '../../shared/components/Icon'
import type { OperationOutcome } from '../../app/store'
import type { MemoryEntry } from '../../shared/types'

const CATEGORY_OPTIONS = ['general', 'profile', 'work', 'projects', 'preferences']

function formatDate(iso: string | null): string {
  if (!iso) return ''
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleDateString([], { year: 'numeric', month: 'short', day: 'numeric' })
}

function categoryLabel(category: string): string {
  return category.charAt(0).toUpperCase() + category.slice(1)
}

interface MemoryViewProps {
  entries: MemoryEntry[]
  disabled: boolean
  onAdd: (information: string, category?: string) => Promise<OperationOutcome>
  onUpdate: (key: string, information: string, category?: string) => Promise<OperationOutcome>
  onDelete: (key: string) => Promise<OperationOutcome>
  onClearAll: () => Promise<OperationOutcome>
  onExport: () => Promise<OperationOutcome>
  onClearHistory: () => void
}

export function MemoryView({
  entries,
  disabled,
  onAdd,
  onUpdate,
  onDelete,
  onClearAll,
  onExport,
  onClearHistory,
}: MemoryViewProps) {
  const [draft, setDraft] = useState('')
  const [draftCategory, setDraftCategory] = useState('general')
  const [query, setQuery] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('all')
  const [editingKey, setEditingKey] = useState<string | null>(null)
  const [editDraft, setEditDraft] = useState('')
  const [editCategory, setEditCategory] = useState('general')
  const [statusMessage, setStatusMessage] = useState<{ ok: boolean; text: string } | null>(null)
  const [busy, setBusy] = useState(false)
  const [confirmingClear, setConfirmingClear] = useState(false)
  const [confirmingDelete, setConfirmingDelete] = useState<MemoryEntry | null>(null)

  const categories = useMemo(() => {
    const present = new Set(entries.map((entry) => entry.category))
    return ['all', ...Array.from(present).sort()]
  }, [entries])

  const needle = query.trim().toLowerCase()
  const visible = entries.filter(
    (entry) =>
      (categoryFilter === 'all' || entry.category === categoryFilter) &&
      (!needle ||
        entry.text.toLowerCase().includes(needle) ||
        entry.key.toLowerCase().includes(needle)),
  )

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
    const outcome = await run(() => onAdd(information, draftCategory))
    if (outcome.ok) setDraft('')
  }

  function beginEdit(entry: MemoryEntry) {
    setEditingKey(entry.key)
    setEditDraft(entry.text)
    setEditCategory(entry.category)
  }

  async function submitEdit(event: React.FormEvent) {
    event.preventDefault()
    if (!editingKey) return
    const information = editDraft.trim()
    if (!information) {
      setStatusMessage({ ok: false, text: 'Memory text cannot be empty.' })
      return
    }
    const outcome = await run(() => onUpdate(editingKey, information, editCategory))
    if (outcome.ok) setEditingKey(null)
  }

  const editCategoryOptions = CATEGORY_OPTIONS.includes(editCategory)
    ? CATEGORY_OPTIONS
    : [editCategory, ...CATEGORY_OPTIONS]

  return (
    <section className="panel" aria-label="Memory">
      <div className="panel__inner panel__inner--split">
        <div className="panel__column">
          <div className="panel__header">
            <div>
              <h2 className="panel__title">Saved memory</h2>
              <p className="panel__desc">Review and control what the agent remembers.</p>
            </div>
          </div>

          <div className="card">
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
              <label className="visually-hidden" htmlFor="memory-category">
                Category
              </label>
              <select
                id="memory-category"
                className="field__select memory__categoryselect"
                value={draftCategory}
                onChange={(event) => setDraftCategory(event.target.value)}
                disabled={busy || disabled}
              >
                {CATEGORY_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {categoryLabel(option)}
                  </option>
                ))}
              </select>
              <button type="submit" className="btn btn--primary" disabled={busy || disabled}>
                {busy ? (
                  <span className="spinner" aria-hidden="true" />
                ) : (
                  <Icon name="plus" size={16} />
                )}
                Add memory
              </button>
            </form>

            {entries.length > 0 ? (
              <>
                <div className="memory__search">
                  <label className="visually-hidden" htmlFor="memory-search">
                    Search memory
                  </label>
                  <input
                    id="memory-search"
                    className="field__input"
                    type="search"
                    placeholder="Search memory…"
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                  />
                </div>
                {categories.length > 2 ? (
                  <div className="chips" role="group" aria-label="Filter by category">
                    {categories.map((category) => (
                      <button
                        key={category}
                        type="button"
                        className="chip"
                        aria-pressed={categoryFilter === category}
                        onClick={() => setCategoryFilter(category)}
                      >
                        {category === 'all' ? 'All' : categoryLabel(category)}
                      </button>
                    ))}
                  </div>
                ) : null}
              </>
            ) : null}

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
            ) : visible.length === 0 ? (
              <p className="empty">No memory matches the current search or filter.</p>
            ) : (
              <ul className="memory__list">
                {visible.map((entry) =>
                  editingKey === entry.key ? (
                    <li key={entry.key} className="memory__item memory__item--editing">
                      <form className="memory__editform" onSubmit={submitEdit}>
                        <label className="visually-hidden" htmlFor={`edit-${entry.key}`}>
                          Edit {entry.key}
                        </label>
                        <input
                          id={`edit-${entry.key}`}
                          className="field__input"
                          type="text"
                          value={editDraft}
                          maxLength={4000}
                          autoFocus
                          onChange={(event) => setEditDraft(event.target.value)}
                          disabled={busy}
                        />
                        <label className="visually-hidden" htmlFor={`edit-category-${entry.key}`}>
                          Category for {entry.key}
                        </label>
                        <select
                          id={`edit-category-${entry.key}`}
                          className="field__select memory__categoryselect"
                          value={editCategory}
                          onChange={(event) => setEditCategory(event.target.value)}
                          disabled={busy}
                        >
                          {editCategoryOptions.map((option) => (
                            <option key={option} value={option}>
                              {categoryLabel(option)}
                            </option>
                          ))}
                        </select>
                        <button type="submit" className="btn btn--primary" disabled={busy}>
                          Save
                        </button>
                        <button
                          type="button"
                          className="btn btn--ghost"
                          onClick={() => setEditingKey(null)}
                          disabled={busy}
                        >
                          Cancel
                        </button>
                      </form>
                    </li>
                  ) : (
                    <li key={entry.key} className="memory__item">
                      <div className="memory__body">
                        <p className="memory__text">{entry.text}</p>
                        <p className="memory__meta">
                          <span className={`memory__category memory__category--${entry.category}`}>
                            {categoryLabel(entry.category)}
                          </span>
                          <span className="memory__key">{entry.key}</span>
                          {entry.updated ? <span>Updated {formatDate(entry.updated)}</span> : null}
                        </p>
                      </div>
                      <button
                        type="button"
                        className="iconbtn"
                        aria-label={`Edit ${entry.key}`}
                        onClick={() => beginEdit(entry)}
                        disabled={busy || disabled}
                      >
                        <Icon name="edit" size={16} />
                      </button>
                      <button
                        type="button"
                        className="iconbtn iconbtn--danger"
                        aria-label={`Forget ${entry.key}`}
                        onClick={() => setConfirmingDelete(entry)}
                        disabled={busy || disabled}
                      >
                        <Icon name="trash" size={16} />
                      </button>
                    </li>
                  ),
                )}
              </ul>
            )}

            <p className="privacy-note">
              <Icon name="shield" size={14} />
              Stored locally in <code>data/memory.json</code> on this computer — nothing is sent
              anywhere else.
            </p>
          </div>
        </div>

        <div className="panel__column panel__column--side">
          <div className="card">
            <h3 className="card__title">Data controls</h3>
            <ul className="controls__list">
              <li>
                <button
                  type="button"
                  className="controlrow"
                  onClick={() => void run(onExport)}
                  disabled={busy || disabled}
                >
                  <Icon name="download" size={17} />
                  <span>
                    <span className="controlrow__label">Export my data</span>
                    <span className="controlrow__help">Download memory, preferences, and history as JSON.</span>
                  </span>
                </button>
              </li>
              <li>
                <button
                  type="button"
                  className="controlrow"
                  onClick={onClearHistory}
                  disabled={busy || disabled}
                >
                  <Icon name="clock" size={17} />
                  <span>
                    <span className="controlrow__label">Clear conversation history</span>
                    <span className="controlrow__help">Removes this session’s history. Memory is kept.</span>
                  </span>
                </button>
              </li>
              <li>
                <button
                  type="button"
                  className="controlrow controlrow--danger"
                  onClick={() => setConfirmingClear(true)}
                  disabled={busy || disabled || entries.length === 0}
                >
                  <Icon name="trash" size={17} />
                  <span>
                    <span className="controlrow__label">Delete all memory</span>
                    <span className="controlrow__help">Permanently removes everything saved.</span>
                  </span>
                </button>
              </li>
            </ul>
            <p className="privacy-note">Destructive actions always require confirmation.</p>
          </div>
        </div>
      </div>

      {confirmingDelete ? (
        <ConfirmDialog
          title={`Forget ${confirmingDelete.key}?`}
          message={`“${confirmingDelete.text}” will be permanently removed. This cannot be undone.`}
          confirmLabel="Forget it"
          busy={busy}
          onCancel={() => setConfirmingDelete(null)}
          onConfirm={() => {
            const key = confirmingDelete.key
            void run(() => onDelete(key)).then(() => setConfirmingDelete(null))
          }}
        />
      ) : null}

      {confirmingClear ? (
        <ConfirmDialog
          title="Delete all memory?"
          message="Every saved entry will be permanently removed from data/memory.json. This action cannot be undone."
          confirmLabel="Delete all memory"
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
