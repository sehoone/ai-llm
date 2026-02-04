import api from './axios'
import type {
  ChatHistoryResponse,
  ChatRequest,
  ChatResponse,
  ChatSession,
  CreateSessionResponse,
  Message,
} from '@/types/chat-api'

const AUTH_BASE = '/api/v1/auth'
const CHATBOT_BASE = '/api/v1/chatbot'

export const chatService = {
  // Admin Operations
  getAllChatHistory: async (limit = 100, offset = 0): Promise<ChatHistoryResponse[]> => {
    const response = await api.get<ChatHistoryResponse[]>(`${CHATBOT_BASE}/history/all`, {
      params: { limit, offset }
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
    const formData = new FormData()
    formData.append('name', name)
    const response = await api.patch<CreateSessionResponse>(
      `${CHATBOT_BASE}/session/${sessionId}/name`,
      formData
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

  // Note: Streaming needs special handling, we'll expose a URL generator or fetch directly in component
  // because axios doesn't support streaming nicely in all environments, but we can try.
  streamMessage: async (
    sessionId: string,
    messages: Message[],
    onChunk: (content: string, done: boolean, title?: string) => void,
    onError: (error: any) => void,
    isDeepThinking?: boolean
  ) => {
    const request: ChatRequest = { session_id: sessionId, messages, is_deep_thinking: isDeepThinking }

    try {
      let buffer = ''
      let processedIndex = 0

      await api.post(`${CHATBOT_BASE}/chat/stream`, request, {
        onDownloadProgress: (progressEvent) => {
          const xhr = progressEvent.event?.target as any
          if (!xhr) return

          const responseText = xhr.responseText || ''
          const newContent = responseText.substring(processedIndex)
          processedIndex = responseText.length

          buffer += newContent

          const lines = buffer.split('\n\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            const trimmedLine = line.trim()
            if (trimmedLine.startsWith('data: ')) {
              const dataStr = trimmedLine.replace('data: ', '')
              try {
                if (dataStr === '[DONE]') {
                  continue
                }
                const data = JSON.parse(dataStr)
                if (data.type === 'title' && data.title) {
                  onChunk('', false, data.title)
                } else {
                  onChunk(data.content, data.done)
                }
              } catch (e) {
                console.error('Error parsing stream chunk', e, 'chunk:', dataStr)
              }
            }
          }
        },
      })

      // Process any remaining buffer
      if (buffer.trim()) {
        const lines = buffer.split('\n\n')
        for (const line of lines) {
          const trimmedLine = line.trim()
          if (trimmedLine.startsWith('data: ')) {
            const dataStr = trimmedLine.replace('data: ', '')
            try {
              const data = JSON.parse(dataStr)
              onChunk(data.content, data.done)
            } catch (e) {
              // Ignore incomplete JSON at the very end
            }
          }
        }
      }
    } catch (e) {
      onError(e)
    }
  }
}
