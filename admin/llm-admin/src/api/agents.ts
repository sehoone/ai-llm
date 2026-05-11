/* eslint-disable @typescript-eslint/no-explicit-any */
import { createSSEProgressHandler } from '@/lib/sse-stream'
import api from './axios'
import type { Message } from '@/types/chat-api'

export interface Agent {
  id: string
  user_id: number
  name: string
  description?: string
  system_prompt?: string
  welcome_message?: string
  model: string
  temperature: number
  max_tokens: number
  rag_keys: string[]
  rag_groups: string[]
  rag_search_k: number
  rag_enabled: boolean
  tools_enabled: string[]
  allowed_models: string[]
  is_published: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CreateAgentData {
  name: string
  description?: string
  system_prompt?: string
  welcome_message?: string
  model?: string
  temperature?: number
  max_tokens?: number
  rag_keys?: string[]
  rag_groups?: string[]
  rag_search_k?: number
  rag_enabled?: boolean
  tools_enabled?: string[]
  allowed_models?: string[]
  is_published?: boolean
}

export interface UpdateAgentData extends Partial<CreateAgentData> {
  is_active?: boolean
}

export interface AgentSession {
  session_id: string
  agent_id: string
  name: string
  created_at: string
}

export interface RagKeyInfo {
  rag_key: string
  rag_group: string
  doc_count: number
  latest_upload?: string
}

export interface RagGroupInfo {
  rag_group: string
  key_count: number
  doc_count: number
  latest_upload?: string
}

export const agentApi = {
  // ── CRUD ──────────────────────────────────────────────────────────────────
  getAll: async (): Promise<Agent[]> => {
    const response = await api.get<Agent[]>('v1/agents/')
    return response.data
  },

  get: async (id: string): Promise<Agent> => {
    const response = await api.get<Agent>(`v1/agents/${id}`)
    return response.data
  },

  create: async (data: CreateAgentData): Promise<Agent> => {
    const response = await api.post<Agent>('v1/agents/', data)
    return response.data
  },

  update: async (id: string, data: UpdateAgentData): Promise<Agent> => {
    const response = await api.put<Agent>(`v1/agents/${id}`, data)
    return response.data
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`v1/agents/${id}`)
  },

  togglePublish: async (id: string): Promise<Agent> => {
    const response = await api.post<Agent>(`v1/agents/${id}/publish`)
    return response.data
  },

  // ── RAG keys / groups ─────────────────────────────────────────────────────
  getRagKeys: async (): Promise<RagKeyInfo[]> => {
    const response = await api.get<RagKeyInfo[]>('v1/agents/rag-keys')
    return response.data
  },

  getRagGroups: async (): Promise<RagGroupInfo[]> => {
    const response = await api.get<RagGroupInfo[]>('v1/agents/rag-groups')
    return response.data
  },

  // ── Sessions ──────────────────────────────────────────────────────────────
  createSession: async (agentId: string): Promise<AgentSession> => {
    const response = await api.post<AgentSession>(`v1/agents/${agentId}/sessions`)
    return response.data
  },

  getSessions: async (agentId: string): Promise<AgentSession[]> => {
    const response = await api.get<AgentSession[]>(`v1/agents/${agentId}/sessions`)
    return response.data
  },

  renameSession: async (agentId: string, sessionId: string, name: string): Promise<AgentSession> => {
    const response = await api.patch<AgentSession>(`v1/agents/${agentId}/sessions/${sessionId}/name`, { name })
    return response.data
  },

  deleteSession: async (agentId: string, sessionId: string): Promise<void> => {
    await api.delete(`v1/agents/${agentId}/sessions/${sessionId}`)
  },

  // ── Messages ──────────────────────────────────────────────────────────────
  getMessages: async (agentId: string, sessionId: string): Promise<Message[]> => {
    const response = await api.get<{ messages: Message[] }>(`v1/agents/${agentId}/messages`, {
      params: { session_id: sessionId },
    })
    return response.data.messages
  },

  // ── Chat (streaming) ──────────────────────────────────────────────────────
  streamMessage: async (
    agentId: string,
    sessionId: string,
    messages: Message[],
    onChunk: (content: string, done: boolean, title?: string) => void,
    onError: (error: any) => void,
    isDeepThinking?: boolean,
    llmResourceId?: number,
    ragGroup?: string
  ) => {
    const request = {
      session_id: sessionId,
      messages,
      is_deep_thinking: isDeepThinking,
      llm_resource_id: llmResourceId || undefined,
      rag_group: ragGroup || undefined,
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
      await api.post(`v1/agents/${agentId}/chat/stream`, request, { onDownloadProgress: handler.onDownloadProgress })
      handler.flush()
    } catch (e) {
      onError(e)
    }
  },
}
