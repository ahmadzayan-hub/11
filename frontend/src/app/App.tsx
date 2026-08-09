import { useCallback, useEffect, useRef, useState } from 'react'
import { ActivityView } from '../features/activity/ActivityView'
import { ChatView } from '../features/chat/ChatView'
import type { ComposerHandle } from '../features/chat/Composer'
import { CommandPalette } from '../features/commands/CommandPalette'
import { HelpDialog } from '../features/commands/HelpDialog'
import { MemoryView } from '../features/memory/MemoryView'
import { Onboarding } from '../features/onboarding/Onboarding'
import { PreferencesView } from '../features/preferences/PreferencesView'
import { ConfirmDialog } from '../shared/components/ConfirmDialog'
import { Icon } from '../shared/components/Icon'
import type { IconName } from '../shared/components/Icon'
import { StatusBadge } from '../shared/components/StatusBadge'
import type { CommandInfo } from '../shared/types'
import { useStore } from './store'
import { useTheme } from './useTheme'

type Tab = 'chat' | 'memory' | 'preferences' | 'activity'

const TABS: Array<{ id: Tab; label: string; icon: IconName }> = [
  { id: 'chat', label: 'Conversation', icon: 'chat' },
  { id: 'memory', label: 'Memory', icon: 'memory' },
  { id: 'preferences', label: 'Preferences', icon: 'settings' },
  { id: 'activity', label: 'Activity', icon: 'activity' },
]

const ONBOARDING_KEY = 'aos-onboarded'

export function App() {
  const store = useStore()
  const { isDark, toggleTheme } = useTheme()
  const [tab, setTab] = useState<Tab>('chat')
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [helpOpen, setHelpOpen] = useState(false)
  const [confirming, setConfirming] = useState<'history' | 'end' | null>(null)
  const [confirmBusy, setConfirmBusy] = useState(false)
  const [showOnboarding, setShowOnboarding] = useState(() => {
    try {
      return localStorage.getItem(ONBOARDING_KEY) !== '1'
    } catch {
      return false
    }
  })
  const composerRef = useRef<ComposerHandle | null>(null)

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setPaletteOpen((open) => !open)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  const dismissOnboarding = useCallback(() => {
    setShowOnboarding(false)
    try {
      localStorage.setItem(ONBOARDING_KEY, '1')
    } catch {
      /* localStorage unavailable — the dialog simply reappears next visit */
    }
  }, [])

  function pickCommand(command: CommandInfo) {
    setPaletteOpen(false)
    setTab('chat')
    const hasArguments = command.usage.trim() !== command.command
    composerRef.current?.insert(hasArguments ? `${command.command} ` : command.command)
  }

  async function confirmAction() {
    setConfirmBusy(true)
    if (confirming === 'history') {
      await store.clearHistory()
    } else if (confirming === 'end') {
      await store.endSession()
    }
    setConfirmBusy(false)
    setConfirming(null)
  }

  const { session, bootError, status } = store

  if (!session) {
    return (
      <div className="shell">
        <header className="shell__header">
          <div className="brand">
            <span className="brand__mark" aria-hidden="true">
              A
            </span>
            <span className="brand__name">Agentic OS</span>
          </div>
        </header>
        <div className="empty" style={{ margin: 'auto' }}>
          {bootError ? (
            <>
              <div className="empty__icon">
                <Icon name="alert" size={32} />
              </div>
              <p>{bootError}</p>
              <p style={{ marginTop: 'var(--space-4)' }}>
                <button type="button" className="btn btn--primary" onClick={() => void store.start()}>
                  <Icon name="refresh" size={16} />
                  Try again
                </button>
              </p>
            </>
          ) : (
            <>
              <span className="spinner" aria-hidden="true" style={{ width: 24, height: 24 }} />
              <p role="status" style={{ marginTop: 'var(--space-3)' }}>
                Starting your session…
              </p>
            </>
          )}
        </div>
      </div>
    )
  }

  const memoryCount = Object.keys(session.memory).length

  const sidebar = (
    <div className="sidebar">
      <p className="sidebar__label">Workspace</p>
      <nav className="sidebar__nav" aria-label="Main">
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            className="navbtn"
            aria-current={tab === item.id ? 'page' : undefined}
            onClick={() => {
              setTab(item.id)
              setDrawerOpen(false)
            }}
          >
            <Icon name={item.icon} size={18} />
            {item.label}
            {item.id === 'memory' && memoryCount > 0 ? (
              <span className="navbtn__badge">{memoryCount}</span>
            ) : null}
          </button>
        ))}
      </nav>
      <div className="sidebar__footer">
        <button
          type="button"
          className="btn btn--ghost"
          onClick={() => {
            void store.start()
            setTab('chat')
            setDrawerOpen(false)
          }}
        >
          <Icon name="refresh" size={16} />
          New session
        </button>
        <button
          type="button"
          className="btn btn--subtle"
          onClick={() => {
            setConfirming('history')
            setDrawerOpen(false)
          }}
          disabled={session.ended || session.history.length === 0}
        >
          <Icon name="trash" size={16} />
          Clear history
        </button>
        <button
          type="button"
          className="btn btn--subtle"
          onClick={() => {
            setConfirming('end')
            setDrawerOpen(false)
          }}
          disabled={session.ended}
        >
          <Icon name="power" size={16} />
          End session
        </button>
      </div>
    </div>
  )

  return (
    <div className="shell">
      <a className="skiplink" href="#composer-input">
        Skip to message composer
      </a>
      <header className="shell__header">
        <button
          type="button"
          className="iconbtn menubtn"
          aria-label="Open navigation"
          aria-expanded={drawerOpen}
          onClick={() => setDrawerOpen(true)}
        >
          <Icon name="menu" />
        </button>
        <div className="brand">
          <span className="brand__mark" aria-hidden="true">
            A
          </span>
          <div>
            <h1 className="brand__name" style={{ fontSize: 'var(--text-l)' }}>
              {session.agent_name}
            </h1>
          </div>
          <span className="brand__version">v{session.version}</span>
        </div>
        <div className="header__spacer" />
        <StatusBadge status={status} />
        <div className="header__actions">
          <button
            type="button"
            className="iconbtn iconbtn--palette"
            aria-label="Search commands (Ctrl+K)"
            title="Search commands (Ctrl+K)"
            onClick={() => setPaletteOpen(true)}
          >
            <Icon name="command" />
          </button>
          <button
            type="button"
            className="iconbtn"
            aria-label={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
            onClick={toggleTheme}
          >
            <Icon name={isDark ? 'sun' : 'moon'} />
          </button>
          <button
            type="button"
            className="iconbtn"
            aria-label="Help and commands"
            onClick={() => setHelpOpen(true)}
          >
            <Icon name="help" />
          </button>
        </div>
      </header>

      <div className="shell__body">
        {sidebar}

        {drawerOpen ? (
          <>
            <button
              type="button"
              className="scrim"
              aria-label="Close navigation"
              onClick={() => setDrawerOpen(false)}
            />
            <div className="drawer">{sidebar}</div>
          </>
        ) : null}

        <main className="main">
          {tab === 'chat' ? (
            <ChatView
              session={session}
              sending={store.sending}
              failedText={store.failedText}
              offline={status === 'offline'}
              onSend={(text) => void store.send(text)}
              onRetry={() => void store.retryFailed()}
              onDismissFailed={store.dismissFailed}
              composerRef={composerRef}
            />
          ) : null}
          {tab === 'memory' ? (
            <MemoryView
              memory={session.memory}
              disabled={session.ended}
              onAdd={store.addMemory}
              onDelete={store.deleteMemory}
              onClearAll={store.clearMemory}
            />
          ) : null}
          {tab === 'preferences' ? (
            <PreferencesView
              preferences={session.preferences}
              disabled={session.ended}
              onSet={store.setPreference}
            />
          ) : null}
          {tab === 'activity' ? <ActivityView events={store.events} /> : null}
        </main>

        <aside className="rail" aria-label="Session overview">
          <div className="rail__section">
            <h2 className="rail__title">Session</h2>
            <dl>
              <div className="rail__row">
                <dt>Agent</dt>
                <dd>{session.agent_name}</dd>
              </div>
              <div className="rail__row">
                <dt>Messages</dt>
                <dd>{session.transcript.length}</dd>
              </div>
              <div className="rail__row">
                <dt>Memory entries</dt>
                <dd>{memoryCount}</dd>
              </div>
              <div className="rail__row">
                <dt>Tone</dt>
                <dd>{String(session.preferences.tone ?? 'friendly')}</dd>
              </div>
            </dl>
          </div>
          <div className="rail__section">
            <h2 className="rail__title">Recent activity</h2>
            {store.events.length === 0 ? (
              <p className="rail__event">No activity yet.</p>
            ) : (
              store.events.slice(0, 6).map((event) => (
                <p key={event.id} className="rail__event">
                  <span className={`dot dot--${event.kind}`} aria-hidden="true" />
                  {event.label}
                </p>
              ))
            )}
          </div>
        </aside>
      </div>

      {paletteOpen ? (
        <CommandPalette
          commands={session.commands}
          onPick={pickCommand}
          onClose={() => setPaletteOpen(false)}
        />
      ) : null}
      {helpOpen ? <HelpDialog commands={session.commands} onClose={() => setHelpOpen(false)} /> : null}
      {showOnboarding ? <Onboarding onDismiss={dismissOnboarding} /> : null}
      {confirming ? (
        <ConfirmDialog
          title={confirming === 'history' ? 'Clear conversation history?' : 'End this session?'}
          message={
            confirming === 'history'
              ? 'The recorded history of this session will be removed. Saved memory is not affected.'
              : 'The agent will say goodbye and this session will close. Saved memory and preferences in config.json are kept.'
          }
          confirmLabel={confirming === 'history' ? 'Clear history' : 'End session'}
          busy={confirmBusy}
          onCancel={() => setConfirming(null)}
          onConfirm={() => void confirmAction()}
        />
      ) : null}
    </div>
  )
}
