import api from './axios'
import type { ChatMessage } from '@/features/sample/data/schema'

// ── Types ─────────────────────────────────────────────────────────────────────

export type BasicChatRequest = { message: string; session_id?: string; system_instructions?: string }
export type BasicChatResponse = { session_id: string; response: string }
export type HistoryResponse = { session_id: string; messages: ChatMessage[] }

export type DeepThinkingRequest = { message: string; session_id?: string; is_deep_thinking?: boolean }
export type DeepThinkingResponse = { session_id: string; response: string; sections: string[] }

export type LLMCallRequest = { message: string; model_name?: string }
export type LLMCallResponse = { response: string; model_used?: string | null }

export type SearchRequest = { query: string; rag_key?: string; top_k?: number }
export type AskRequest = { question: string; rag_key?: string; session_id?: string }
export type AskResponse = { answer: string; rag_key: string; session_id: string; retrieved_chunks: number }

export type NodeDef = { id: string; node_type: string; config: Record<string, unknown>; dependencies?: string[] }
export type WorkflowRunRequest = { name?: string; nodes: NodeDef[]; input?: Record<string, unknown> }

export type BusinessOpRequest = { operation: string; payload?: Record<string, unknown> | null }

// ── SSE Stream Helper ─────────────────────────────────────────────────────────

export type SseCallbacks = {
  onToken: (token: string) => void
  onEvent?: (event: string, data: string) => void
  onSessionId?: (session_id: string) => void
  onDone?: () => void
}

const parseSseChunk = (chunk: string, cb: SseCallbacks) => {
  const lines = chunk.split('\n')
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim()
    if (line.startsWith('event: ')) {
      const event = line.slice(7)
      i++
      const dataLine = lines[i]?.trim()
      if (dataLine?.startsWith('data: ')) {
        cb.onEvent?.(event, dataLine.slice(6))
      }
      continue
    }
    if (!line.startsWith('data: ')) continue
    const text = line.slice(6)
    if (text === '[DONE]') { cb.onDone?.(); continue }
    if (!text) continue
    try {
      const parsed = JSON.parse(text)
      if (parsed.session_id) cb.onSessionId?.(parsed.session_id)
    } catch {
      cb.onToken(text.replace(/\\n/g, '\n'))
    }
  }
}

const streamPost = (endpoint: string, body: object, cb: SseCallbacks): Promise<void> => {
  let buffer = ''
  return api.post<string>(endpoint, body, {
    responseType: 'text',
    onDownloadProgress: (evt) => {
      const raw = (evt.event.target as XMLHttpRequest).responseText
      const chunk = raw.slice(buffer.length)
      buffer = raw
      parseSseChunk(chunk, cb)
    },
  }).then(() => undefined)
}

// ── 01 Basic Chat ─────────────────────────────────────────────────────────────

export const sendChat = async (data: BasicChatRequest): Promise<BasicChatResponse> =>
  (await api.post('v1/sample/basic-chat/chat', data)).data

export const getChatHistory = async (session_id: string): Promise<HistoryResponse> =>
  (await api.get('v1/sample/basic-chat/history', { params: { session_id } })).data

export const streamChat = (data: BasicChatRequest, cb: SseCallbacks): Promise<void> =>
  streamPost('v1/sample/basic-chat/stream', data, cb)

// ── 02 Deep Thinking ──────────────────────────────────────────────────────────

export const sendDeepThinking = async (data: DeepThinkingRequest): Promise<DeepThinkingResponse> =>
  (await api.post('v1/sample/deep-thinking/chat', data)).data

export const streamDeepThinking = (data: DeepThinkingRequest, cb: SseCallbacks): Promise<void> =>
  streamPost('v1/sample/deep-thinking/stream', data, cb)

// ── 03 LLM Service ────────────────────────────────────────────────────────────

export const getLlmInfo = async () => (await api.get('v1/sample/llm/info')).data
export const callLlm = async (data: LLMCallRequest): Promise<LLMCallResponse> =>
  (await api.post('v1/sample/llm/call', data)).data
export const getCircuitBreakers = async () => (await api.get('v1/sample/llm/circuit-breakers')).data

// ── 04 RAG Pipeline ───────────────────────────────────────────────────────────

export const uploadRagDocument = async (file: File, rag_key?: string) => {
  const form = new FormData()
  form.append('file', file)
  if (rag_key) form.append('rag_key', rag_key)
  return (await api.post('v1/sample/rag/upload', form, { headers: { 'Content-Type': 'multipart/form-data' } })).data
}

export const searchRag = async (data: SearchRequest) =>
  (await api.post('v1/sample/rag/search', data)).data

export const askRag = async (data: AskRequest): Promise<AskResponse> =>
  (await api.post('v1/sample/rag/ask', data)).data

export const deleteRagDocs = async (rag_key?: string) =>
  (await api.delete('v1/sample/rag/docs', { params: rag_key ? { rag_key } : {} })).data

// ── 05 FastAPI Patterns ───────────────────────────────────────────────────────

export type StreamDemoRequest = { message: string; delay_ms?: number; session_id?: string }

export const streamBasicPattern = (data: StreamDemoRequest, cb: SseCallbacks): Promise<void> =>
  streamPost('v1/sample/patterns/stream/basic', data, cb)

export const streamSectionedPattern = (data: StreamDemoRequest, cb: SseCallbacks): Promise<void> =>
  streamPost('v1/sample/patterns/stream/sectioned', data, cb)

export const getRateLimitTest = async () => (await api.get('v1/sample/patterns/rate-limit-test')).data
export const getMiddlewareInfo = async () => (await api.get('v1/sample/patterns/middleware-info')).data

// ── 06 Workflow Engine ────────────────────────────────────────────────────────

export const getNodeTypes = async () => (await api.get('v1/sample/workflow/node-types')).data
export const getWorkflowPresets = async () => (await api.get('v1/sample/workflow/presets')).data
export const runWorkflow = async (data: WorkflowRunRequest) =>
  (await api.post('v1/sample/workflow/run', data)).data
export const streamWorkflow = (data: WorkflowRunRequest, cb: SseCallbacks): Promise<void> =>
  streamPost('v1/sample/workflow/run/stream', data, cb)

// ── 07 Database Patterns ──────────────────────────────────────────────────────

export const getDbHealth = async () => (await api.get('v1/sample/db/health')).data
export const getDbUsers = async () => (await api.get('v1/sample/db/users')).data
export const getDbUserCount = async () => (await api.get('v1/sample/db/users/count')).data
export const getDbPoolStats = async () => (await api.get('v1/sample/db/pool-stats')).data

// ── 08 Observability ──────────────────────────────────────────────────────────

export const getLogDemo = async (level = 'info') =>
  (await api.get('v1/sample/observability/log-demo', { params: { level } })).data

export const businessOp = async (data: BusinessOpRequest) =>
  (await api.post('v1/sample/observability/business-op', data)).data

export const getObservabilityContext = async () =>
  (await api.get('v1/sample/observability/context')).data

export const getMetricsDemo = async (model = 'gpt-4o') =>
  (await api.get('v1/sample/observability/metrics-demo', { params: { model } })).data
