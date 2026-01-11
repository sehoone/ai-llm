export interface FileAttachment {
  filename: string
  content_type: string
  data: string // Base64
}

export interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string
  files?: FileAttachment[]
  created_at?: string
}

export interface ChatRequest {
  session_id: string
  messages: Message[]
}

export interface ChatResponse {
  messages: Message[]
}

export interface StreamResponse {
  content: string
  done: boolean
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
