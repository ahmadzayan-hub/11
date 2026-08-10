import type { ExportPayload, RunDetail, RunSummary, SessionState, TranscriptEntry } from './types'

const API_BASE = import.meta.env.VITE_API_BASE ?? ''
const REQUEST_TIMEOUT_MS = 10_000

export class ApiError extends Error {
  status: number
  offline: boolean

  constructor(message: string, status = 0, offline = false) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.offline = offline
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  timeoutMs = REQUEST_TIMEOUT_MS,
): Promise<T> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...init,
      signal: controller.signal,
    })
  } catch (error) {
    const timedOut = error instanceof DOMException && error.name === 'AbortError'
    throw new ApiError(
      timedOut
        ? 'The server took too long to respond. Please try again.'
        : 'Cannot reach the Agentic OS server. Check your connection.',
      0,
      !timedOut,
    )
  } finally {
    clearTimeout(timer)
  }

  let body: unknown = null
  try {
    body = await response.json()
  } catch {
    body = null
  }

  if (!response.ok) {
    const detail =
      body && typeof body === 'object' && 'detail' in body && typeof body.detail === 'string'
        ? body.detail
        : `Request failed (${response.status}).`
    throw new ApiError(detail, response.status)
  }
  return body as T
}

export interface OperationResult {
  reply_text: string
  state: SessionState
}

export interface MessageResult {
  reply: TranscriptEntry
  state: SessionState
}

export const api = {
  health: () => request<{ status: string; agent_name: string; version: string }>('/api/health'),
  createSession: () => request<SessionState>('/api/sessions', { method: 'POST' }),
  getSession: (id: string) => request<SessionState>(`/api/sessions/${id}`),
  endSession: (id: string) => request<SessionState>(`/api/sessions/${id}`, { method: 'DELETE' }),
  sendMessage: (id: string, text: string) =>
    request<MessageResult>(`/api/sessions/${id}/messages`, {
      method: 'POST',
      body: JSON.stringify({ text }),
    }),
  clearHistory: (id: string) =>
    request<OperationResult>(`/api/sessions/${id}/history`, { method: 'DELETE' }),
  setPreference: (id: string, key: string, value: string) =>
    request<OperationResult>(`/api/sessions/${id}/preferences`, {
      method: 'PUT',
      body: JSON.stringify({ key, value }),
    }),
  addMemory: (id: string, information: string, category?: string) =>
    request<OperationResult>(`/api/sessions/${id}/memory`, {
      method: 'POST',
      body: JSON.stringify({ information, category: category ?? null }),
    }),
  updateMemory: (id: string, key: string, information: string, category?: string) =>
    request<OperationResult>(`/api/sessions/${id}/memory/${encodeURIComponent(key)}`, {
      method: 'PUT',
      body: JSON.stringify({ information, category: category ?? null }),
    }),
  deleteMemory: (id: string, key: string) =>
    request<OperationResult>(`/api/sessions/${id}/memory/${encodeURIComponent(key)}`, {
      method: 'DELETE',
    }),
  exportData: (id: string) => request<ExportPayload>(`/api/sessions/${id}/export`),
  clearMemory: (id: string) =>
    request<OperationResult>(`/api/sessions/${id}/memory`, { method: 'DELETE' }),
  createRun: (goal: string, datasetText?: string, datasetName?: string) =>
    request<RunDetail>('/api/runs', {
      method: 'POST',
      body: JSON.stringify({
        goal,
        dataset_text: datasetText ?? null,
        dataset_name: datasetName ?? null,
      }),
    }),
  listRuns: () => request<{ runs: RunSummary[] }>('/api/runs'),
  getRun: (id: string) => request<RunDetail>(`/api/runs/${id}`),
  advanceRun: (id: string) => request<RunDetail>(`/api/runs/${id}/advance`, { method: 'POST' }),
  cancelRun: (id: string) => request<RunDetail>(`/api/runs/${id}/cancel`, { method: 'POST' }),
  decideApproval: (id: string, approvalId: string, decision: 'approve' | 'reject') =>
    request<RunDetail>(`/api/runs/${id}/approvals/${approvalId}`, {
      method: 'POST',
      body: JSON.stringify({ decision }),
    }),
}
