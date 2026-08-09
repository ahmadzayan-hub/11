export interface TranscriptEntry {
  id: number
  role: 'user' | 'agent'
  text: string
  time: string
}

export interface CommandInfo {
  command: string
  usage: string
  description: string
}

export type PreferenceValue = string | boolean

export interface SessionState {
  session_id: string
  agent_name: string
  version: string
  welcome: string
  ended: boolean
  created_at: string
  transcript: TranscriptEntry[]
  preferences: Record<string, PreferenceValue>
  memory: Record<string, string>
  history: string[]
  memory_persisted: boolean
  commands: CommandInfo[]
}

export interface ExportPayload {
  exported_at: string
  agent_name: string
  preferences: Record<string, PreferenceValue>
  memory: Record<string, string>
  history: string[]
  transcript: TranscriptEntry[]
}

export type ActivityKind = 'info' | 'success' | 'error'

export interface ActivityEvent {
  id: number
  label: string
  detail?: string
  kind: ActivityKind
  time: string
}

export type ConnectionStatus = 'ready' | 'working' | 'offline' | 'error' | 'ended'
