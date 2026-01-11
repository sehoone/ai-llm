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
    const response = await api.get<ChatSession[]>(`${AUTH_BASE}/sessions`)
    return response.data
  },

  createSession: async (): Promise<CreateSessionResponse> => {
    const response = await api.post<CreateSessionResponse>(
      `${AUTH_BASE}/session`
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
      `${AUTH_BASE}/session/${sessionId}/name`,
      formData
    )
    return response.data
  },

  deleteSession: async (sessionId: string): Promise<void> => {
    await api.delete(`${AUTH_BASE}/session/${sessionId}`)
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
    messages: Message[]
  ): Promise<Message[]> => {
    const request: ChatRequest = { session_id: sessionId, messages }
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
    onChunk: (content: string, done: boolean) => void,
    onError: (error: any) => void
  ) => {
    const request: ChatRequest = { session_id: sessionId, messages }
    
    // Using fetch for streaming as it's easier to handle ReadableStream
    const token = api.defaults.headers.common['Authorization'] || 
                  (api.interceptors.request as any)?.handlers?.[0]?.fulfilled?.({headers:{}})?.headers?.Authorization;
    
    // We need to get the actual token from the store or interception if possible. 
    // Since we can't easily access the interceptor's dynamic token here purely,
    // we assume the component calling this might handle it, OR we import the store.
    // Importing store here is fine as it's client-side.
    
    // Dynamic import to avoid issues if used on server (though this is client specific)
    const { useAuthStore } = await import('@/stores/auth-store')
    const accessToken = useAuthStore.getState().auth.accessToken

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || ''}${CHATBOT_BASE}/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`,
        },
        body: JSON.stringify(request),
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      if (!reader) throw new Error('No reader available')

      while (true) {
        const { value, done } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n\n')
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.replace('data: ', '')
            try {
              const data = JSON.parse(dataStr)
              onChunk(data.content, data.done)
            } catch (e) {
              console.error('Error parsing stream chunk', e)
            }
          }
        }
      }
    } catch (e) {
      onError(e)
    }
  }
}
