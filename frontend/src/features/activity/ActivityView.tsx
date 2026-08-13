import { useEffect, useState } from 'react'
import { api } from '../../shared/api'
import { Icon } from '../../shared/components/Icon'
import type { IconName } from '../../shared/components/Icon'
import type { ActivityEvent, ConnectionStatus, SessionState, Usage } from '../../shared/types'

function formatBytes(bytes: number): string {
  if (bytes < 1000) return `${bytes} B`
  if (bytes < 1_000_000) return `${(bytes / 1000).toFixed(1)} kB`
  return `${(bytes / 1_000_000).toFixed(1)} MB`
}

/** A limit the server enforces but the interface never shows is a trap:
 *  the first a user hears of it is a refusal. */
function UsageCard() {
  const [usage, setUsage] = useState<Usage | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let cancelled = false
    api
      .usage()
      .then((result) => !cancelled && setUsage(result))
      .catch(() => !cancelled && setFailed(true))
    return () => {
      cancelled = true
    }
  }, [])

  if (failed) {
    return (
      <div className="card">
        <h3 className="card__title">Usage</h3>
        <p className="controlrow__help">Usage could not be read from the server.</p>
      </div>
    )
  }
  if (!usage) {
    return (
      <div className="card">
        <h3 className="card__title">Usage</h3>
        <div className="skeleton skeleton--line" />
        <div className="skeleton skeleton--line" />
      </div>
    )
  }

  const rows = [
    {
      key: 'runs',
      label: 'Runs today',
      used: `${usage.runs_today.used} of ${usage.runs_today.limit}`,
      share: usage.runs_today.limit ? usage.runs_today.used / usage.runs_today.limit : 0,
      help: `Resets at midnight UTC. ${usage.runs_today.remaining} left.`,
    },
    {
      key: 'datasets',
      label: 'Datasets stored',
      used: `${usage.datasets.used} of ${usage.datasets.limit}`,
      share: usage.datasets.limit ? usage.datasets.used / usage.datasets.limit : 0,
      help: 'Re-running a stored dataset costs nothing.',
    },
    {
      key: 'bytes',
      label: 'Storage used',
      used: `${formatBytes(usage.dataset_bytes.used)} of ${formatBytes(usage.dataset_bytes.limit)}`,
      share: usage.dataset_bytes.limit ? usage.dataset_bytes.used / usage.dataset_bytes.limit : 0,
      help: 'Uploading the same file twice stores it once.',
    },
  ]

  return (
    <div className="card">
      <h3 className="card__title">Usage</h3>
      <ul className="usage">
        {rows.map((row) => (
          <li key={row.key} className="usage__row">
            <div className="usage__head">
              <span className="controlrow__label">{row.label}</span>
              <span className="usage__value">{row.used}</span>
            </div>
            <div
              className="usage__track"
              role="meter"
              aria-valuenow={Math.round(row.share * 100)}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`${row.label}: ${row.used}`}
            >
              <div
                className={`usage__fill ${row.share >= 0.9 ? 'usage__fill--high' : ''}`}
                style={{ width: `${Math.min(100, Math.round(row.share * 100))}%` }}
              />
            </div>
            <span className="controlrow__help">{row.help}</span>
          </li>
        ))}
      </ul>
      <p className="privacy-note">
        Not measured: {usage.not_tracked.join(', ')}.
      </p>
    </div>
  )
}

type ActivityFilter = 'all' | 'system' | 'memory' | 'preferences' | 'errors'

const FILTERS: Array<{ id: ActivityFilter; label: string }> = [
  { id: 'all', label: 'All' },
  { id: 'system', label: 'System' },
  { id: 'memory', label: 'Memory' },
  { id: 'preferences', label: 'Preferences' },
  { id: 'errors', label: 'Errors' },
]

function filterOf(event: ActivityEvent): ActivityFilter {
  if (event.kind === 'error') return 'errors'
  if (/memory|data export/i.test(event.label)) return 'memory'
  if (/preference/i.test(event.label)) return 'preferences'
  return 'system'
}

function formatTime(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

const EVENT_ICONS: Array<{ match: RegExp; icon: IconName }> = [
  { match: /session/i, icon: 'power' },
  { match: /preference/i, icon: 'settings' },
  { match: /memory|data/i, icon: 'memory' },
  { match: /history/i, icon: 'clock' },
  { match: /connection/i, icon: 'refresh' },
]

function iconFor(label: string): IconName {
  return EVENT_ICONS.find((entry) => entry.match.test(label))?.icon ?? 'activity'
}

interface ActivityViewProps {
  events: ActivityEvent[]
  session: SessionState
  status: ConnectionStatus
  lastSyncedAt: string | null
}

/** Operational transparency: real events and real health facts only —
 *  no fabricated telemetry, no hidden reasoning. */
export function ActivityView({ events, session, status, lastSyncedAt }: ActivityViewProps) {
  const [filter, setFilter] = useState<ActivityFilter>('all')
  const online = status !== 'offline'
  const healthy = online && status !== 'error'
  const visible = filter === 'all' ? events : events.filter((event) => filterOf(event) === filter)

  return (
    <section className="panel" aria-label="Activity">
      <div className="panel__inner panel__inner--split">
        <div className="panel__column">
          <div className="panel__header">
            <div>
              <h2 className="panel__title">Activity</h2>
              <p className="panel__desc">
                What the agent has done this session — status only, never private reasoning.
              </p>
            </div>
          </div>

          {events.length > 0 ? (
            <div className="chips" role="group" aria-label="Filter activity">
              {FILTERS.map((option) => (
                <button
                  key={option.id}
                  type="button"
                  className="chip"
                  aria-pressed={filter === option.id}
                  onClick={() => setFilter(option.id)}
                >
                  {option.label}
                </button>
              ))}
            </div>
          ) : null}

          {events.length === 0 ? (
            <div className="card">
              <div className="empty">
                <div className="empty__icon">
                  <Icon name="activity" size={32} />
                </div>
                <p>No activity yet. Events appear here as you interact with the agent.</p>
              </div>
            </div>
          ) : visible.length === 0 ? (
            <div className="card">
              <p className="empty">No {filter} events in this session yet.</p>
            </div>
          ) : (
            <div className="card">
              <ol className="timeline">
                {visible.map((event) => (
                  <li key={event.id} className="timeline__item">
                    <span className={`timeline__icon timeline__icon--${event.kind}`} aria-hidden="true">
                      <Icon name={iconFor(event.label)} size={16} />
                    </span>
                    <div className="timeline__body">
                      <p className="activity__label">{event.label}</p>
                      {event.detail ? <p className="activity__detail">{event.detail}</p> : null}
                    </div>
                    <time className="activity__time" dateTime={event.time}>
                      {formatTime(event.time)}
                    </time>
                  </li>
                ))}
              </ol>
            </div>
          )}
        </div>

        <div className="panel__column panel__column--side">
          <div className="card">
            <h3 className="card__title">Session health</h3>
            <ul className="health">
              <li className="health__row">
                <span
                  className={`health__dot ${healthy ? 'health__dot--ok' : 'health__dot--bad'}`}
                  aria-hidden="true"
                />
                <span>
                  <span className="controlrow__label">{online ? 'Agent online' : 'Agent offline'}</span>
                  <span className="controlrow__help">
                    {healthy
                      ? 'Connected and responsive.'
                      : online
                        ? 'The last request failed — retry from the conversation.'
                        : 'Requests will fail until the connection returns.'}
                  </span>
                </span>
              </li>
              <li className="health__row">
                <span
                  className={`health__dot ${session.memory_persisted ? 'health__dot--ok' : 'health__dot--warn'}`}
                  aria-hidden="true"
                />
                <span>
                  <span className="controlrow__label">
                    {session.memory_persisted ? 'Local storage active' : 'Memory not persisted'}
                  </span>
                  <span className="controlrow__help">
                    {session.memory_persisted
                      ? 'Memory is saved to data/memory.json on this computer.'
                      : 'No memory file is configured — memory lasts this session only.'}
                  </span>
                </span>
              </li>
              <li className="health__row">
                <span className="health__dot health__dot--ok" aria-hidden="true" />
                <span>
                  <span className="controlrow__label">
                    {Object.keys(session.memory).length} memory entr
                    {Object.keys(session.memory).length === 1 ? 'y' : 'ies'}
                  </span>
                  <span className="controlrow__help">
                    {session.transcript.length} messages in this session.
                  </span>
                </span>
              </li>
              <li className="health__row">
                <span
                  className={`health__dot ${lastSyncedAt ? 'health__dot--ok' : 'health__dot--warn'}`}
                  aria-hidden="true"
                />
                <span>
                  <span className="controlrow__label">
                    {lastSyncedAt ? `Last response ${formatTime(lastSyncedAt)}` : 'No responses yet'}
                  </span>
                  <span className="controlrow__help">Time of the last successful server reply.</span>
                </span>
              </li>
            </ul>
          </div>

          <UsageCard />
        </div>
      </div>
    </section>
  )
}
