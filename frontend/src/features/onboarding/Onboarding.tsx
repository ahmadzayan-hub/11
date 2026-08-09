import { Dialog } from '../../shared/components/Dialog'
import { Icon } from '../../shared/components/Icon'

const POINTS = [
  {
    icon: 'chat',
    text: 'Talk to the agent in plain language, or use slash commands like /help and /remember.',
  },
  {
    icon: 'command',
    text: 'Press Ctrl+K (or ⌘K) any time to search every available command.',
  },
  {
    icon: 'settings',
    text: 'Preferences such as response tone change how the agent replies — instantly.',
  },
  {
    icon: 'memory',
    text: 'Memory is stored locally in data/memory.json and persists between sessions. You can clear it whenever you like.',
  },
] as const

interface OnboardingProps {
  onDismiss: () => void
}

/** Short, optional first-run introduction. Shown once; dismissible forever. */
export function Onboarding({ onDismiss }: OnboardingProps) {
  return (
    <Dialog title="Welcome to Agentic OS" onClose={onDismiss} labelledById="onboarding-title">
      <p className="dialog__body">
        Your personal intelligent workspace: conversation, memory, and preferences in one place.
      </p>
      <ul className="onboard__list">
        {POINTS.map((point) => (
          <li key={point.text} className="onboard__item">
            <span className="onboard__icon">
              <Icon name={point.icon} size={18} />
            </span>
            <span>{point.text}</span>
          </li>
        ))}
      </ul>
      <div className="dialog__actions">
        <button type="button" className="btn btn--primary" onClick={onDismiss}>
          Get started
        </button>
      </div>
    </Dialog>
  )
}
