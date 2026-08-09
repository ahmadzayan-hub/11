import type { ConnectionStatus } from '../types'

const LABELS: Record<ConnectionStatus, string> = {
  ready: 'Ready',
  working: 'Working',
  offline: 'Offline',
  error: 'Error',
  ended: 'Session ended',
}

/** Live session status shown in the header and announced to screen readers. */
export function StatusBadge({ status }: { status: ConnectionStatus }) {
  return (
    <span className={`badge badge--${status}`} role="status" aria-live="polite">
      <span className="badge__dot" aria-hidden="true" />
      {LABELS[status]}
    </span>
  )
}
