import { useState } from 'react'
import { useMotion } from '../../app/useMotion'
import { useTheme } from '../../app/useTheme'
import type { ThemeChoice } from '../../app/useTheme'
import type { OperationOutcome } from '../../app/store'
import type { PreferenceValue } from '../../shared/types'

const TONES = ['friendly', 'concise', 'formal'] as const
const THEMES: Array<{ id: ThemeChoice; label: string }> = [
  { id: 'dark', label: 'Dark' },
  { id: 'light', label: 'Light' },
  { id: 'system', label: 'System' },
]

interface PreferencesViewProps {
  preferences: Record<string, PreferenceValue>
  disabled: boolean
  onSet: (key: string, value: string) => Promise<OperationOutcome>
}

export function PreferencesView({ preferences, disabled, onSet }: PreferencesViewProps) {
  const { theme, setTheme } = useTheme()
  const { reducedMotion, setReducedMotion } = useMotion()
  const [statusMessage, setStatusMessage] = useState<{ ok: boolean; text: string } | null>(null)
  const [busyKey, setBusyKey] = useState<string | null>(null)
  const [languageDraft, setLanguageDraft] = useState(String(preferences.language ?? 'English'))
  const [nameDraft, setNameDraft] = useState(String(preferences.user_name ?? ''))

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
      <div className="panel__inner panel__inner--split">
        <div className="panel__column">
          <div className="panel__header">
            <div>
              <h2 className="panel__title">Response preferences</h2>
              <p className="panel__desc">
                Control how the agent responds. Changes apply to the current session; permanent
                defaults live in <code>config.json</code>.
              </p>
            </div>
          </div>

          <div className="card">
            <div className="field">
              <span className="field__label" id="tone-label">
                Tone
              </span>
              <span className="field__help" id="tone-help">
                How the agent phrases its replies.
              </span>
              <div
                className="segmented"
                role="group"
                aria-labelledby="tone-label"
                aria-describedby="tone-help"
              >
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
                const value = nameDraft.trim()
                if (value) void apply('user_name', value)
              }}
            >
              <label className="field__label" htmlFor="pref-name">
                Your name
              </label>
              <span className="field__help">Used to greet you in the workspace.</span>
              <div className="field__row">
                <input
                  id="pref-name"
                  className="field__input"
                  type="text"
                  placeholder="e.g. Ahmad"
                  value={nameDraft}
                  maxLength={200}
                  onChange={(event) => setNameDraft(event.target.value)}
                  disabled={busyKey !== null || disabled}
                />
                <button
                  type="submit"
                  className="btn btn--ghost"
                  disabled={busyKey !== null || disabled || !nameDraft.trim()}
                >
                  Save
                </button>
              </div>
            </form>

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
              <div className="field__row">
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

        <div className="panel__column panel__column--side">
          <div className="card">
            <h3 className="card__title">Interface</h3>
            <p className="panel__desc">Stored in this browser only.</p>

            <div className="field">
              <span className="field__label" id="theme-label">
                Theme
              </span>
              <div className="segmented" role="group" aria-labelledby="theme-label">
                {THEMES.map((option) => (
                  <button
                    key={option.id}
                    type="button"
                    className="segmented__option"
                    aria-pressed={theme === option.id}
                    onClick={() => setTheme(option.id)}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="field">
              <div className="switchrow">
                <div>
                  <span className="field__label" id="motion-label">
                    Reduced motion
                  </span>
                  <p className="field__help">Minimize animations. System settings are always honored.</p>
                </div>
                <button
                  type="button"
                  role="switch"
                  aria-checked={reducedMotion}
                  aria-labelledby="motion-label"
                  className="switch"
                  onClick={() => setReducedMotion(!reducedMotion)}
                >
                  <span className="switch__thumb" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
