import { useState } from 'react'
import type { OperationOutcome } from '../../app/store'
import type { PreferenceValue } from '../../shared/types'

const TONES = ['friendly', 'concise', 'formal'] as const

interface PreferencesViewProps {
  preferences: Record<string, PreferenceValue>
  disabled: boolean
  onSet: (key: string, value: string) => Promise<OperationOutcome>
}

export function PreferencesView({ preferences, disabled, onSet }: PreferencesViewProps) {
  const [statusMessage, setStatusMessage] = useState<{ ok: boolean; text: string } | null>(null)
  const [busyKey, setBusyKey] = useState<string | null>(null)
  const [languageDraft, setLanguageDraft] = useState(String(preferences.language ?? 'English'))

  const tone = String(preferences.tone ?? 'friendly')
  const saveHistory = preferences.save_history !== false

  async function apply(key: string, value: string) {
    setBusyKey(key)
    const outcome = await onSet(key, value)
    setStatusMessage({ ok: outcome.ok, text: outcome.message })
    setBusyKey(null)
  }

  return (
    <section className="panel" aria-label="Preferences">
      <div className="panel__inner">
        <div className="panel__header">
          <div>
            <h2 className="panel__title">Preferences</h2>
            <p className="panel__desc">
              Changes apply to the current session immediately. Permanent defaults live in{' '}
              <code>config.json</code>.
            </p>
          </div>
        </div>

        <div className="card">
          <div className="field">
            <span className="field__label" id="tone-label">
              Response tone
            </span>
            <span className="field__help" id="tone-help">
              How the agent phrases its replies.
            </span>
            <div className="segmented" role="group" aria-labelledby="tone-label" aria-describedby="tone-help">
              {TONES.map((option) => (
                <button
                  key={option}
                  type="button"
                  className="segmented__option"
                  aria-pressed={tone === option}
                  disabled={busyKey !== null || disabled}
                  onClick={() => void apply('tone', option)}
                >
                  {option.charAt(0).toUpperCase() + option.slice(1)}
                </button>
              ))}
            </div>
          </div>

          <form
            className="field"
            onSubmit={(event) => {
              event.preventDefault()
              const value = languageDraft.trim()
              if (value) void apply('language', value)
            }}
          >
            <label className="field__label" htmlFor="pref-language">
              Language
            </label>
            <span className="field__help">
              Recorded with your preferences; the current agent replies in English.
            </span>
            <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
              <input
                id="pref-language"
                className="field__input"
                type="text"
                value={languageDraft}
                maxLength={200}
                onChange={(event) => setLanguageDraft(event.target.value)}
                disabled={busyKey !== null || disabled}
              />
              <button
                type="submit"
                className="btn btn--ghost"
                disabled={busyKey !== null || disabled || !languageDraft.trim()}
              >
                Save
              </button>
            </div>
          </form>

          <div className="field">
            <div className="switchrow">
              <div>
                <span className="field__label" id="history-label">
                  Record session history
                </span>
                <p className="field__help">
                  When off, your requests are not recorded in this session’s history.
                </p>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={saveHistory}
                aria-labelledby="history-label"
                className="switch"
                disabled={busyKey !== null || disabled}
                onClick={() => void apply('save_history', saveHistory ? 'false' : 'true')}
              >
                <span className="switch__thumb" />
              </button>
            </div>
          </div>
        </div>

        <p
          className={`statusline ${
            statusMessage ? (statusMessage.ok ? 'statusline--success' : 'statusline--error') : ''
          }`}
          role="status"
          aria-live="polite"
        >
          {busyKey ? 'Saving…' : (statusMessage?.text ?? '')}
        </p>
      </div>
    </section>
  )
}
