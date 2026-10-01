export interface FileAttachment {
  filename: string
  content_type: string
  data: string // Base64 — realtime send only
}

export interface AttachmentMeta {
  id: number
  filename: string
  content_type: string
  file_size: number
}

export interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string
  files?: FileAttachment[]        // realtime send (base64)
  attachments?: AttachmentMeta[]  // history (metadata only)
  created_at?: string
}

export interface ChatRequest {
  session_id: string
  messages: Message[]
  is_deep_thinking?: boolean
  rag_group?: string
  llm_resource_id?: number
}

export interface ChatResponse {
  messages: Message[]
}

export type StreamEventType =
  | 'content'
  | 'title'
  | 'artifact_start'
  | 'artifact_delta'
  | 'artifact_end'

export interface StreamResponse {
  content: string
  done: boolean
  type?: StreamEventType
  title?: string
  artifact_id?: string
  artifact_type?: string
  artifact_title?: string
  version?: number
}

/** The six supported artifact content types. */
export type ArtifactType =
  | 'text/html'
  | 'application/vnd.react'
  | 'image/svg+xml'
  | 'application/vnd.mermaid'
  | 'text/markdown'
  | 'application/vnd.code'

/** A streaming/open artifact held in the client store (keyed by identifier). */
export interface ArtifactState {
  identifier: string
  type: string
  title: string
  content: string
  version: number
  isStreaming: boolean
  serverId?: string // artifact.id (uuid), resolved after stream completes
}

/** Discriminated artifact events surfaced to the chat stream consumer. */
export type ArtifactStreamEvent =
  | { kind: 'start'; identifier: string; type: string; title: string }
  | { kind: 'delta'; identifier: string; text: string }
  | { kind: 'end'; identifier: string; version?: number }

export interface ArtifactSummary {
  id: string
  session_id: string
  identifier: string
  artifact_type: string
  title: string
  current_version: number
  is_published: boolean
  public_token?: string | null
  created_at: string
  updated_at: string
}

export interface ArtifactDetail extends ArtifactSummary {
  content: string
}

export interface ArtifactVersionItem {
  version: number
  content: string
  created_at: string
}

export interface ChatSession {
  session_id: string
  name: string | null
  created_at?: string
}

export interface CreateSessionResponse {
  session_id: string
  name: string | null
}

export interface ChatHistoryResponse {
  id: number
  session_id: string
  user_email: string
  question: string
  answer: string
  created_at: string
  session_name: string | null
  attachments: AttachmentMeta[]
}

export interface ChatHistoryListResponse {
  items: ChatHistoryResponse[]
  total: number
}
