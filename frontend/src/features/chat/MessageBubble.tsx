import { useState } from 'react'
import { Icon } from '../../shared/components/Icon'
import type { TranscriptEntry } from '../../shared/types'

function formatTime(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

interface MessageBubbleProps {
  entry: TranscriptEntry
  agentName: string
}

export function MessageBubble({ entry, agentName }: MessageBubbleProps) {
  const [copied, setCopied] = useState(false)
  const isAgent = entry.role === 'agent'

  async function copy() {
    try {
      await navigator.clipboard.writeText(entry.text)
      setCopied(true)
      setTimeout(() => setCopied(false), 1600)
    } catch {
      // Clipboard unavailable (permissions/insecure context) — leave silently.
    }
  }

  return (
    <article className={`msg msg--${entry.role}`} aria-label={isAgent ? 'Agent message' : 'Your message'}>
      {isAgent ? (
        <div className="msg__head">
          <span className="msg__avatar" aria-hidden="true">
            A
          </span>
          <span className="msg__author">{agentName}</span>
          <time dateTime={entry.time}>{formatTime(entry.time)}</time>
        </div>
      ) : null}
      <div className="msg__bubble">{entry.text}</div>
      <div className="msg__meta">
        {isAgent ? (
          <button type="button" className="msg__copy" onClick={copy}>
            <Icon name={copied ? 'check' : 'copy'} size={13} />
            {copied ? 'Copied' : 'Copy'}
          </button>
        ) : (
          <time dateTime={entry.time}>{formatTime(entry.time)}</time>
        )}
      </div>
    </article>
  )
}
