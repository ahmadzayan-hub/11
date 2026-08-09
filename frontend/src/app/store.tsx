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
  start: () => Promise<void>
  send: (text: string) => Promise<void>
  retryFailed: () => Promise<void>
  dismissFailed: () => void
  clearHistory: () => Promise<OperationOutcome>
  setPreference: (key: string, value: string) => Promise<OperationOutcome>
  addMemory: (information: string) => Promise<OperationOutcome>
  deleteMemory: (key: string) => Promise<OperationOutcome>
  clearMemory: () => Promise<OperationOutcome>
  endSession: () => Promise<OperationOutcome>
}

const StoreContext = createContext<Store | null>(null)

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
      setFailedText(null)
      setLastError(false)
      pushEvent('Session started', 'success', state.agent_name)
    } catch (error) {
      const message = error instanceof ApiError ? error.message : 'Could not start a session.'
      setBootError(message)
      pushEvent('Session start failed', 'error', message)
    } finally {
      endWork()
    }
  }, [beginWork, endWork, pushEvent])

  const startedOnce = useRef(false)
  useEffect(() => {
    // Guard against React StrictMode double-invoking the mount effect in
    // development, which would otherwise open two sessions.
    if (startedOnce.current) return
    startedOnce.current = true
    void start()
    // start() is stable; run once on mount.
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
    (information: string) => runOperation((id) => api.addMemory(id, information), 'Memory saved'),
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
      start,
      send,
      retryFailed,
      dismissFailed,
      clearHistory,
      setPreference,
      addMemory,
      deleteMemory,
      clearMemory,
      endSession,
    }),
    [
      session,
      bootError,
      status,
      sending,
      failedText,
      events,
      start,
      send,
      retryFailed,
      dismissFailed,
      clearHistory,
      setPreference,
      addMemory,
      deleteMemory,
      clearMemory,
      endSession,
    ],
  )

  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>
}
