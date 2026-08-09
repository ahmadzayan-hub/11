import { Icon } from '../../shared/components/Icon'
import type { ActivityEvent } from '../../shared/types'

function formatTime(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

/** Chronological feed of real operational events from this session. */
export function ActivityView({ events }: { events: ActivityEvent[] }) {
  return (
    <section className="panel" aria-label="Activity">
      <div className="panel__inner">
        <div className="panel__header">
          <div>
            <h2 className="panel__title">Activity</h2>
            <p className="panel__desc">
              A live record of what the agent has done this session — newest first.
            </p>
          </div>
        </div>

        {events.length === 0 ? (
          <div className="empty">
            <div className="empty__icon">
              <Icon name="activity" size={32} />
            </div>
            <p>No activity yet. Events appear here as you interact with the agent.</p>
          </div>
        ) : (
          <div className="card">
            <ol className="activity__list">
              {events.map((event) => (
                <li key={event.id} className="activity__item">
                  <span className={`dot dot--${event.kind}`} aria-hidden="true" />
                  <div>
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
    </section>
  )
}
