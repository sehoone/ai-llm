/* eslint-disable @typescript-eslint/no-explicit-any */
import { createSSEProgressHandler } from '@/lib/sse-stream'
import api from './axios'
import type {
  AttachmentMeta,
  ChatHistoryListResponse,
  ChatHistoryResponse,
  ChatRequest,
  ChatResponse,
  ChatSession,
  CreateSessionResponse,
  Message,
} from '@/types/chat-api'

// const AUTH_BASE = '/api/v1/auth'
const CHATBOT_BASE = 'v1/chatbot'

export const chatService = {
  // Admin Operations
  getAllChatHistory: async (limit = 10, offset = 0, search = ''): Promise<ChatHistoryListResponse> => {
    const response = await api.get<ChatHistoryListResponse>(`${CHATBOT_BASE}/history/all`, {
      params: { limit, offset, search: search || undefined }
    })
    return response.data
  },

  getChatHistoryDetail: async (messageId: number): Promise<ChatHistoryResponse> => {
    const response = await api.get<ChatHistoryResponse>(`${CHATBOT_BASE}/history/${messageId}`)
    return response.data
  },

  // Session Management
  getSessions: async (): Promise<ChatSession[]> => {
    const response = await api.get<ChatSession[]>(`${CHATBOT_BASE}/sessions`)
    return response.data
  },

  createSession: async (): Promise<CreateSessionResponse> => {
    const response = await api.post<CreateSessionResponse>(
      `${CHATBOT_BASE}/session`
    )
    return response.data
  },

  renameSession: async (
    sessionId: string,
    name: string
  ): Promise<CreateSessionResponse> => {
    const response = await api.patch<CreateSessionResponse>(
      `${CHATBOT_BASE}/session/${sessionId}/name`,
      { name }
    )
    return response.data
  },

  deleteSession: async (sessionId: string): Promise<void> => {
    await api.delete(`${CHATBOT_BASE}/session/${sessionId}`)
  },

  // Chat Operations
  getMessages: async (sessionId: string): Promise<Message[]> => {
    const response = await api.get<ChatResponse>(`${CHATBOT_BASE}/messages`, {
      params: { session_id: sessionId },
    })
    return response.data.messages
  },

  sendMessage: async (
    sessionId: string,
    messages: Message[],
    isDeepThinking?: boolean
  ): Promise<Message[]> => {
    const request: ChatRequest = { session_id: sessionId, messages, is_deep_thinking: isDeepThinking }
    const response = await api.post<ChatResponse>(
      `${CHATBOT_BASE}/chat`,
      request
    )
    return response.data.messages
  },

  clearHistory: async (sessionId: string): Promise<void> => {
    await api.delete(`${CHATBOT_BASE}/messages`, {
      params: { session_id: sessionId },
    })
  },

  downloadAttachment: async (attachment: AttachmentMeta): Promise<void> => {
    const response = await api.get(`${CHATBOT_BASE}/attachments/${attachment.id}`, {
      responseType: 'blob',
    })
    const url = URL.createObjectURL(response.data)
    const a = document.createElement('a')
    a.href = url
    a.download = attachment.filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  },

  // Note: Streaming needs special handling, we'll expose a URL generator or fetch directly in component
  // because axios doesn't support streaming nicely in all environments, but we can try.
  streamMessage: async (
    sessionId: string,
    messages: Message[],
    onChunk: (content: string, done: boolean, title?: string) => void,
    onError: (error: any) => void,
    isDeepThinking?: boolean,
    ragGroup?: string,
    llmResourceId?: number
  ) => {
    const request: ChatRequest = {
      session_id: sessionId,
      messages,
      is_deep_thinking: isDeepThinking,
      rag_group: ragGroup || undefined,
      llm_resource_id: llmResourceId || undefined,
    }

    try {
      const handler = createSSEProgressHandler<{ content: string; done: boolean; type?: string; title?: string }>(
        (data) => {
          if (data.type === 'title' && data.title) {
            onChunk('', false, data.title)
          } else {
            onChunk(data.content, data.done)
          }
        }
      )
      await api.post(`${CHATBOT_BASE}/chat/stream`, request, { onDownloadProgress: handler.onDownloadProgress })
      handler.flush()
    } catch (e) {
      onError(e)
    }
  }
}
