import { useEffect, useRef, useState } from 'react'
import { Icon } from '../../shared/components/Icon'
import type { IconName } from '../../shared/components/Icon'
import type { SessionState } from '../../shared/types'
import { Composer } from './Composer'
import type { ComposerHandle } from './Composer'
import { MessageBubble } from './MessageBubble'

export interface Suggestion {
  label: string
  icon: IconName
  insert: string
}

export const SUGGESTIONS: Suggestion[] = [
  { label: 'See what the agent can do', icon: 'help', insert: '/help' },
  { label: 'Remember something', icon: 'memory', insert: '/remember ' },
  { label: 'Switch to concise replies', icon: 'sparkle', insert: '/set tone concise' },
  { label: 'Show session history', icon: 'clock', insert: '/history' },
]

function greetingFor(hour: number, name: string | null): string {
  const period = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening'
  return name ? `${period}, ${name}` : period
}

interface ChatViewProps {
  session: SessionState
  sending: boolean
  failedText: string | null
  offline: boolean
  userName: string | null
  onSend: (text: string) => void
  onRetry: () => void
  onDismissFailed: () => void
  composerRef: React.RefObject<ComposerHandle | null>
}

export function ChatView({
  session,
  sending,
  failedText,
  offline,
  userName,
  onSend,
  onRetry,
  onDismissFailed,
  composerRef,
}: ChatViewProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [pinnedToBottom, setPinnedToBottom] = useState(true)
  const transcriptLength = session.transcript.length

  // Follow new messages only while the reader is already at the bottom, so
  // auto-scroll never fights manual scrolling through older messages.
  useEffect(() => {
    const container = scrollRef.current
    if (container && pinnedToBottom) {
      container.scrollTop = container.scrollHeight
    }
  }, [transcriptLength, sending, pinnedToBottom])

  function handleScroll() {
    const container = scrollRef.current
    if (!container) return
    const distance = container.scrollHeight - container.scrollTop - container.clientHeight
    setPinnedToBottom(distance < 48)
  }

  // A failed or in-flight first message must render the stream (with its
  // retry affordance), not the empty-state hero.
  const empty = transcriptLength === 0 && !failedText && !sending

  return (
    <section className="chat" aria-label="Conversation">
      <div className="chat__scroll" ref={scrollRef} onScroll={handleScroll}>
        {empty ? (
          <div className="chat__empty">
            <div className="hero__orb" aria-hidden="true">
              <Icon name="sparkle" size={26} />
            </div>
            <h2 className="hero__greeting">{greetingFor(new Date().getHours(), userName)}</h2>
            <p className="hero__question">What would you like to accomplish?</p>
            <div className="suggestions">
              {SUGGESTIONS.map((suggestion) => (
                <button
                  key={suggestion.label}
                  type="button"
                  className="suggestion"
                  onClick={() => composerRef.current?.insert(suggestion.insert)}
                >
                  <Icon name={suggestion.icon} size={16} />
                  {suggestion.label}
                </button>
              ))}
            </div>
            <p className="hero__hint">
              {session.welcome} Commands begin with <kbd>/</kbd> — browse them any time with{' '}
              <kbd>Ctrl</kbd>+<kbd>K</kbd>.
            </p>
          </div>
        ) : (
          <div className="chat__stream" aria-live="polite">
            {session.transcript.map((entry) => (
              <MessageBubble key={entry.id} entry={entry} agentName={session.agent_name} />
            ))}
            {sending ? (
              <div className="typing" role="status" aria-label="The agent is preparing a response">
                <span className="typing__dot" />
                <span className="typing__dot" />
                <span className="typing__dot" />
              </div>
            ) : null}
            {failedText ? (
              <div className="alertbar" role="alert">
                <Icon name="alert" size={16} />
                <span>Your message didn’t go through.</span>
                <button type="button" className="alertbar__retry" onClick={onRetry}>
                  Retry
                </button>
                <button
                  type="button"
                  className="iconbtn"
                  style={{ width: 28, height: 28 }}
                  onClick={onDismissFailed}
                  aria-label="Dismiss error"
                >
                  <Icon name="x" size={14} />
                </button>
              </div>
            ) : null}
            {session.ended ? (
              <div className="alertbar alertbar--info" role="status">
                <Icon name="power" size={16} />
                <span>This session has ended. Start a new session to continue.</span>
              </div>
            ) : null}
          </div>
        )}
      </div>

      {!pinnedToBottom && !empty ? (
        <button
          type="button"
          className="jump"
          onClick={() => {
            const container = scrollRef.current
            if (container) container.scrollTop = container.scrollHeight
            setPinnedToBottom(true)
          }}
        >
          <Icon name="arrowDown" size={14} />
          Latest
        </button>
      ) : null}

      <Composer
        ref={composerRef}
        onSend={onSend}
        busy={sending}
        disabled={session.ended || offline}
      />
    </section>
  )
}
