/* eslint-disable @typescript-eslint/no-explicit-any */
import { logger } from '@/lib/logger'
import api from './axios'
import type { Message, ChatResponse } from '@/types/chat-api'

export interface CustomGPT {
  id: string
  user_id: number
  name: string
  description?: string
  instructions: string
  rag_key: string
  is_public: boolean
  model: string
}

export interface CreateCustomGPTData {
  name: string
  description?: string
  instructions: string
  is_public?: boolean
  model?: string
  rag_key?: string
}

export interface UpdateCustomGPTData {
  name?: string
  description?: string
  instructions?: string
  is_public?: boolean
  model?: string
}

export interface GPTSession {
  session_id: string
  name: string
  custom_gpt_id: string
}

export interface GPTChatRequest {
  session_id: string
  messages: Message[]
  is_deep_thinking?: boolean
}

export const customGptApi = {
  // ── CRUD ─────────────────────────────────────────────────────────────────
  create: async (data: CreateCustomGPTData) => {
    const response = await api.post<CustomGPT>('/api/v1/gpts/', data)
    return response.data
  },

  getAll: async () => {
    const response = await api.get<CustomGPT[]>('/api/v1/gpts/')
    return response.data
  },

  get: async (id: string) => {
    const response = await api.get<CustomGPT>(`/api/v1/gpts/${id}`)
    return response.data
  },

  update: async (id: string, data: UpdateCustomGPTData) => {
    const response = await api.put<CustomGPT>(`/api/v1/gpts/${id}`, data)
    return response.data
  },

  delete: async (id: string) => {
    await api.delete(`/api/v1/gpts/${id}`)
  },

  // ── Session management ────────────────────────────────────────────────────
  createSession: async (gptId: string): Promise<GPTSession> => {
    const response = await api.post<GPTSession>(`/api/v1/gpts/${gptId}/sessions`)
    return response.data
  },

  getSessions: async (gptId: string): Promise<GPTSession[]> => {
    const response = await api.get<GPTSession[]>(`/api/v1/gpts/${gptId}/sessions`)
    return response.data
  },

  renameSession: async (gptId: string, sessionId: string, name: string): Promise<GPTSession> => {
    const formData = new FormData()
    formData.append('name', name)
    const response = await api.patch<GPTSession>(`/api/v1/gpts/${gptId}/sessions/${sessionId}/name`, formData)
    return response.data
  },

  deleteSession: async (gptId: string, sessionId: string): Promise<void> => {
    await api.delete(`/api/v1/gpts/${gptId}/sessions/${sessionId}`)
  },

  // ── Messages ──────────────────────────────────────────────────────────────
  getMessages: async (gptId: string, sessionId: string): Promise<Message[]> => {
    const response = await api.get<ChatResponse>(`/api/v1/gpts/${gptId}/messages`, {
      params: { session_id: sessionId },
    })
    return response.data.messages
  },

  clearMessages: async (gptId: string, sessionId: string): Promise<void> => {
    await api.delete(`/api/v1/gpts/${gptId}/messages`, {
      params: { session_id: sessionId },
    })
  },

  // ── Chat (streaming) ──────────────────────────────────────────────────────
  streamMessage: async (
    gptId: string,
    sessionId: string,
    messages: Message[],
    onChunk: (content: string, done: boolean, title?: string) => void,
    onError: (error: any) => void,
    isDeepThinking?: boolean
  ) => {
    const request: GPTChatRequest = { session_id: sessionId, messages, is_deep_thinking: isDeepThinking }

    try {
      let buffer = ''
      let processedIndex = 0

      await api.post(`/api/v1/gpts/${gptId}/chat/stream`, request, {
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
                if (dataStr === '[DONE]') continue
                const data = JSON.parse(dataStr)
                if (data.type === 'title' && data.title) {
                  onChunk('', false, data.title)
                } else {
                  onChunk(data.content, data.done)
                }
              } catch (e) {
                logger.error('Error parsing GPT stream chunk', e, 'chunk:', dataStr)
              }
            }
          }
        },
      })

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
              logger.error('Error parsing GPT stream chunk at the end', e, 'chunk:', dataStr)
            }
          }
        }
      }
    } catch (e) {
      onError(e)
    }
  },
}
