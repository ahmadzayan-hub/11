import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { api, ApiError } from '../shared/api'
import type { ActivityEvent, ActivityKind, ConnectionStatus, SessionState } from '../shared/types'

export interface OperationOutcome {
  ok: boolean
  message: string
}

interface Store {
  session: SessionState | null
  bootError: string | null
  status: ConnectionStatus
  sending: boolean
  failedText: string | null
  events: ActivityEvent[]
  lastSyncedAt: string | null
  start: () => Promise<void>
  send: (text: string) => Promise<void>
  retryFailed: () => Promise<void>
  dismissFailed: () => void
  clearHistory: () => Promise<OperationOutcome>
  setPreference: (key: string, value: string) => Promise<OperationOutcome>
  addMemory: (information: string, category?: string) => Promise<OperationOutcome>
  updateMemory: (key: string, information: string, category?: string) => Promise<OperationOutcome>
  deleteMemory: (key: string) => Promise<OperationOutcome>
  clearMemory: () => Promise<OperationOutcome>
  exportData: () => Promise<OperationOutcome>
  endSession: () => Promise<OperationOutcome>
}

const StoreContext = createContext<Store | null>(null)

const SESSION_KEY = 'aos-session'

function readStoredSessionId(): string | null {
  try {
    return localStorage.getItem(SESSION_KEY)
  } catch {
    return null
  }
}

function storeSessionId(id: string) {
  try {
    localStorage.setItem(SESSION_KEY, id)
  } catch {
    /* private mode — the session simply won't survive a refresh */
  }
}

export function useStore(): Store {
  const store = useContext(StoreContext)
  if (!store) throw new Error('useStore must be used inside <StoreProvider>')
  return store
}

let eventId = 0

export function StoreProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<SessionState | null>(null)
  const [bootError, setBootError] = useState<string | null>(null)
  const [events, setEvents] = useState<ActivityEvent[]>([])
  const [sending, setSending] = useState(false)
  const [failedText, setFailedText] = useState<string | null>(null)
  const [offline, setOffline] = useState(!navigator.onLine)
  const [lastError, setLastError] = useState(false)
  const [lastSyncedAt, setLastSyncedAt] = useState<string | null>(null)
  const pendingCount = useRef(0)
  const [pending, setPending] = useState(0)

  const pushEvent = useCallback((label: string, kind: ActivityKind, detail?: string) => {
    eventId += 1
    const event: ActivityEvent = {
      id: eventId,
      label,
      kind,
      detail,
      time: new Date().toISOString(),
    }
    setEvents((current) => [event, ...current].slice(0, 100))
  }, [])

  const beginWork = useCallback(() => {
    pendingCount.current += 1
    setPending(pendingCount.current)
  }, [])

  const endWork = useCallback(() => {
    pendingCount.current = Math.max(0, pendingCount.current - 1)
    setPending(pendingCount.current)
  }, [])

  useEffect(() => {
    function goOnline() {
      setOffline(false)
      pushEvent('Connection restored', 'success')
    }
    function goOffline() {
      setOffline(true)
      pushEvent('Connection lost', 'error')
    }
    window.addEventListener('online', goOnline)
    window.addEventListener('offline', goOffline)
    return () => {
      window.removeEventListener('online', goOnline)
      window.removeEventListener('offline', goOffline)
    }
  }, [pushEvent])

  const start = useCallback(async () => {
    beginWork()
    setBootError(null)
    try {
      const state = await api.createSession()
      setSession(state)
      storeSessionId(state.session_id)
      setFailedText(null)
      setLastError(false)
      setLastSyncedAt(new Date().toISOString())
      pushEvent('Session started', 'success', state.agent_name)
    } catch (error) {
      const message = error instanceof ApiError ? error.message : 'Could not start a session.'
      setBootError(message)
      pushEvent('Session start failed', 'error', message)
    } finally {
      endWork()
    }
  }, [beginWork, endWork, pushEvent])

  // On page load, restore the previous session when the server still has
  // it and it hasn't ended; otherwise fall back to a fresh session.
  const bootstrap = useCallback(async () => {
    const storedId = readStoredSessionId()
    if (storedId) {
      beginWork()
      try {
        const state = await api.getSession(storedId)
        if (!state.ended) {
          setSession(state)
          setLastSyncedAt(new Date().toISOString())
          pushEvent('Session restored', 'success', `${state.transcript.length} messages`)
          return
        }
      } catch (error) {
        // Offline or server error: surface it instead of silently
        // replacing the session. A 404 just means the session expired.
        if (error instanceof ApiError && (error.status === 0 || error.status >= 500)) {
          setBootError(error.message)
          pushEvent('Session restore failed', 'error', error.message)
          return
        }
      } finally {
        endWork()
      }
    }
    await start()
  }, [beginWork, endWork, pushEvent, start])

  const startedOnce = useRef(false)
  useEffect(() => {
    // Guard against React StrictMode double-invoking the mount effect in
    // development, which would otherwise open two sessions.
    if (startedOnce.current) return
    startedOnce.current = true
    void bootstrap()
    // bootstrap() is stable; run once on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const send = useCallback(
    async (text: string) => {
      if (!session || sending) return
      setSending(true)
      setFailedText(null)
      beginWork()
      try {
        const result = await api.sendMessage(session.session_id, text)
        setSession(result.state)
        setLastError(false)
        setLastSyncedAt(new Date().toISOString())
        pushEvent('Request completed', 'info', text.length > 60 ? `${text.slice(0, 60)}…` : text)
        if (result.state.ended) pushEvent('Session ended', 'info')
      } catch (error) {
        const message = error instanceof ApiError ? error.message : 'The request failed.'
        setFailedText(text)
        setLastError(true)
        if (error instanceof ApiError && error.offline) setOffline(true)
        pushEvent('Request failed', 'error', message)
      } finally {
        setSending(false)
        endWork()
      }
    },
    [session, sending, beginWork, endWork, pushEvent],
  )

  const retryFailed = useCallback(async () => {
    const text = failedText
    if (!text) return
    setFailedText(null)
    await send(text)
  }, [failedText, send])

  const dismissFailed = useCallback(() => setFailedText(null), [])

  const runOperation = useCallback(
    async (
      operation: (sessionId: string) => Promise<{ reply_text: string; state: SessionState }>,
      successLabel: string,
    ): Promise<OperationOutcome> => {
      if (!session) return { ok: false, message: 'No active session.' }
      beginWork()
      try {
        const result = await operation(session.session_id)
        setSession(result.state)
        setLastError(false)
        setLastSyncedAt(new Date().toISOString())
        pushEvent(successLabel, 'success', result.reply_text)
        return { ok: true, message: result.reply_text }
      } catch (error) {
        const message = error instanceof ApiError ? error.message : 'The request failed.'
        if (error instanceof ApiError && error.offline) setOffline(true)
        setLastError(true)
        pushEvent(`${successLabel} failed`, 'error', message)
        return { ok: false, message }
      } finally {
        endWork()
      }
    },
    [session, beginWork, endWork, pushEvent],
  )

  const clearHistory = useCallback(
    () => runOperation((id) => api.clearHistory(id), 'History cleared'),
    [runOperation],
  )
  const setPreference = useCallback(
    (key: string, value: string) =>
      runOperation((id) => api.setPreference(id, key, value), 'Preference changed'),
    [runOperation],
  )
  const addMemory = useCallback(
    (information: string, category?: string) =>
      runOperation((id) => api.addMemory(id, information, category), 'Memory saved'),
    [runOperation],
  )
  const updateMemory = useCallback(
    (key: string, information: string, category?: string) =>
      runOperation((id) => api.updateMemory(id, key, information, category), 'Memory updated'),
    [runOperation],
  )
  const deleteMemory = useCallback(
    (key: string) => runOperation((id) => api.deleteMemory(id, key), 'Memory removed'),
    [runOperation],
  )
  const clearMemory = useCallback(
    () => runOperation((id) => api.clearMemory(id), 'Memory cleared'),
    [runOperation],
  )

  const exportData = useCallback(async (): Promise<OperationOutcome> => {
    if (!session) return { ok: false, message: 'No active session.' }
    beginWork()
    try {
      const payload = await api.exportData(session.session_id)
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = 'agentic-os-export.json'
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
      setLastSyncedAt(new Date().toISOString())
      pushEvent('Data exported', 'success', 'agentic-os-export.json')
      return { ok: true, message: 'Your data was downloaded as agentic-os-export.json.' }
    } catch (error) {
      const message = error instanceof ApiError ? error.message : 'The export failed.'
      pushEvent('Data export failed', 'error', message)
      return { ok: false, message }
    } finally {
      endWork()
    }
  }, [session, beginWork, endWork, pushEvent])

  const endSession = useCallback(async (): Promise<OperationOutcome> => {
    if (!session) return { ok: false, message: 'No active session.' }
    beginWork()
    try {
      const state = await api.endSession(session.session_id)
      setSession(state)
      pushEvent('Session ended', 'info')
      return { ok: true, message: 'Session ended.' }
    } catch (error) {
      const message = error instanceof ApiError ? error.message : 'The request failed.'
      pushEvent('End session failed', 'error', message)
      return { ok: false, message }
    } finally {
      endWork()
    }
  }, [session, beginWork, endWork, pushEvent])

  const status: ConnectionStatus = offline
    ? 'offline'
    : session?.ended
      ? 'ended'
      : pending > 0
        ? 'working'
        : lastError
          ? 'error'
          : 'ready'

  const value = useMemo<Store>(
    () => ({
      session,
      bootError,
      status,
      sending,
      failedText,
      events,
      lastSyncedAt,
      start,
      send,
      retryFailed,
      dismissFailed,
      clearHistory,
      setPreference,
      addMemory,
      updateMemory,
      deleteMemory,
      clearMemory,
      exportData,
      endSession,
    }),
    [
      session,
      bootError,
      status,
      sending,
      failedText,
      events,
      lastSyncedAt,
      start,
      send,
      retryFailed,
      dismissFailed,
      clearHistory,
      setPreference,
      addMemory,
      updateMemory,
      deleteMemory,
      clearMemory,
      exportData,
      endSession,
    ],
  )

  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>
}
