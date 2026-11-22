/* eslint-disable @typescript-eslint/no-explicit-any */
import { createSSEProgressHandler } from '@/lib/sse-stream'
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
  llm_resource_id?: number
}

export const customGptApi = {
  // ── CRUD ─────────────────────────────────────────────────────────────────
  create: async (data: CreateCustomGPTData) => {
    const response = await api.post<CustomGPT>('v1/gpts/', data)
    return response.data
  },

  getAll: async () => {
    const response = await api.get<CustomGPT[]>('v1/gpts/')
    return response.data
  },

  get: async (id: string) => {
    const response = await api.get<CustomGPT>(`v1/gpts/${id}`)
    return response.data
  },

  update: async (id: string, data: UpdateCustomGPTData) => {
    const response = await api.put<CustomGPT>(`v1/gpts/${id}`, data)
    return response.data
  },

  delete: async (id: string) => {
    await api.delete(`v1/gpts/${id}`)
  },

  // ── Session management ────────────────────────────────────────────────────
  createSession: async (gptId: string): Promise<GPTSession> => {
    const response = await api.post<GPTSession>(`v1/gpts/${gptId}/sessions`)
    return response.data
  },

  getSessions: async (gptId: string): Promise<GPTSession[]> => {
    const response = await api.get<GPTSession[]>(`v1/gpts/${gptId}/sessions`)
    return response.data
  },

  renameSession: async (gptId: string, sessionId: string, name: string): Promise<GPTSession> => {
    const response = await api.patch<GPTSession>(`v1/gpts/${gptId}/sessions/${sessionId}/name`, { name })
    return response.data
  },

  deleteSession: async (gptId: string, sessionId: string): Promise<void> => {
    await api.delete(`v1/gpts/${gptId}/sessions/${sessionId}`)
  },

  // ── Messages ──────────────────────────────────────────────────────────────
  getMessages: async (gptId: string, sessionId: string): Promise<Message[]> => {
    const response = await api.get<ChatResponse>(`v1/gpts/${gptId}/messages`, {
      params: { session_id: sessionId },
    })
    return response.data.messages
  },

  clearMessages: async (gptId: string, sessionId: string): Promise<void> => {
    await api.delete(`v1/gpts/${gptId}/messages`, {
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
    isDeepThinking?: boolean,
    llmResourceId?: number
  ) => {
    const request: GPTChatRequest = { session_id: sessionId, messages, is_deep_thinking: isDeepThinking, llm_resource_id: llmResourceId || undefined }

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
      await api.post(`v1/gpts/${gptId}/chat/stream`, request, { onDownloadProgress: handler.onDownloadProgress })
      handler.flush()
    } catch (e) {
      onError(e)
    }
  },
}
