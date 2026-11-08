/* eslint-disable @typescript-eslint/no-explicit-any */
import { createEventSSEHandler } from '@/lib/sse-stream'
import api from './axios'
import type {
  ApprovalDecision,
  ApprovalRequiredEvent,
  AttachmentMeta,
  ChatHistoryListResponse,
  ChatHistoryResponse,
  ChatSession,
  ChatStreamCallbacks,
  CreateSessionResponse,
  FileAttachment,
  Message,
} from '@/types/chat-api'

// v3 chat 도메인 (ADR-0008). 백엔드는 /api/v1/chat/*, 세션 id는 int·title 기반.
// 이 레이어가 v3 계약을 web 기존 타입(session_id:string, name)으로 어댑트한다.
const CHAT_BASE = 'v1/chat'

/** 백엔드 SessionResponse({id:int, title}) → web ChatSession. */
interface V3Session {
  id: number
  title: string
}
function toChatSession(s: V3Session): ChatSession {
  return { session_id: String(s.id), name: s.title }
}

/** 백엔드 MessageResponse → web Message (표시용 user/assistant만). */
interface V3Message {
  id: number
  role: string
  content: string
  tool_calls?: unknown[] | null
}
function toMessage(m: V3Message): Message {
  // 'tool'·'system' 역할은 표시 union에 없음 → assistant로 귀속.
  const role: Message['role'] = m.role === 'user' ? 'user' : m.role === 'system' ? 'system' : 'assistant'
  return { role, content: m.content }
}

/** 백엔드 ChatHistoryItem(session_id:int) → web ChatHistoryResponse(session_id:string). */
interface V3HistoryItem extends Omit<ChatHistoryResponse, 'session_id'> {
  session_id: number
}
function toHistoryItem(h: V3HistoryItem): ChatHistoryResponse {
  return { ...h, session_id: String(h.session_id) }
}

export const chatService = {
  // ── 세션 관리 ──
  getSessions: async (): Promise<ChatSession[]> => {
    const res = await api.get<V3Session[]>(`${CHAT_BASE}/sessions`)
    return res.data.map(toChatSession)
  },

  createSession: async (title?: string): Promise<CreateSessionResponse> => {
    const res = await api.post<V3Session>(`${CHAT_BASE}/sessions`, { title })
    return toChatSession(res.data)
  },

  renameSession: async (sessionId: string, name: string): Promise<CreateSessionResponse> => {
    const res = await api.patch<V3Session>(`${CHAT_BASE}/sessions/${sessionId}`, { title: name })
    return toChatSession(res.data)
  },

  deleteSession: async (sessionId: string): Promise<void> => {
    await api.delete(`${CHAT_BASE}/sessions/${sessionId}`)
  },

  // ── 메시지 조회 ──
  getMessages: async (sessionId: string): Promise<Message[]> => {
    const res = await api.get<V3Message[]>(`${CHAT_BASE}/sessions/${sessionId}/messages`)
    return res.data.map(toMessage)
  },

  // ── 메시지 전송 (SSE, HITL) ──
  // 평범한 메시지라도 CONFIRM 티어 tool call을 만나면 onApprovalRequired로 끊기고,
  // submitApprovals로 재개하면 최종 message가 이어서 스트림된다 (ADR-0008 §4).
  streamMessage: async (
    sessionId: string,
    content: string,
    callbacks: ChatStreamCallbacks,
    llmResourceId?: number,
    ragGroup?: string,
    files?: FileAttachment[]
  ): Promise<void> => {
    await runSSE(
      `${CHAT_BASE}/sessions/${sessionId}/messages`,
      { content, llm_resource_id: llmResourceId, rag_group: ragGroup, files },
      callbacks
    )
  },

  // ── 승인/거부 결정 제출 → 재개 (SSE) ──
  submitApprovals: async (
    sessionId: string,
    groupKey: string,
    decisions: ApprovalDecision[],
    callbacks: ChatStreamCallbacks
  ): Promise<void> => {
    await runSSE(
      `${CHAT_BASE}/sessions/${sessionId}/approvals`,
      { group_key: groupKey, decisions },
      callbacks
    )
  },

  // ── 관리자 대화 이력 (v3: /api/v1/chat/history/*, 관리자 전용 — 403이면 권한 없음) ──
  // 한 행 = user 메시지(질문) + 뒤이은 assistant 메시지(답변). id는 user 메시지 id.
  getAllChatHistory: async (limit = 10, offset = 0, search = ''): Promise<ChatHistoryListResponse> => {
    const res = await api.get<{ items: V3HistoryItem[]; total: number }>(`${CHAT_BASE}/history/all`, {
      params: { limit, offset, search: search || undefined },
    })
    return { items: res.data.items.map(toHistoryItem), total: res.data.total }
  },

  getChatHistoryDetail: async (messageId: number): Promise<ChatHistoryResponse> => {
    const res = await api.get<V3HistoryItem>(`${CHAT_BASE}/history/${messageId}`)
    return toHistoryItem(res.data)
  },

  downloadAttachment: async (attachment: AttachmentMeta): Promise<void> => {
    const response = await api.get(`${CHAT_BASE}/attachments/${attachment.id}`, {
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
}

/** v3 event-SSE 공통 구동: message/approval_required/done/error 디스패치. */
async function runSSE(url: string, body: unknown, callbacks: ChatStreamCallbacks): Promise<void> {
  try {
    const handler = createEventSSEHandler((event, data) => {
      switch (event) {
        case 'status':
          callbacks.onStatus?.(data?.phase, data?.filename ?? null)
          break
        case 'content':
          callbacks.onContent(data?.delta ?? '')
          break
        case 'message':
          callbacks.onMessage(data)
          break
        case 'artifact_start':
          callbacks.onArtifact({
            kind: 'start',
            identifier: data?.identifier ?? 'artifact',
            type: data?.artifact_type ?? 'text/markdown',
            title: data?.title ?? '',
          })
          break
        case 'artifact_delta':
          callbacks.onArtifact({
            kind: 'delta',
            identifier: data?.identifier ?? 'artifact',
            text: data?.delta ?? '',
          })
          break
        case 'artifact_end':
          callbacks.onArtifact({
            kind: 'end',
            identifier: data?.identifier ?? 'artifact',
            version: data?.version,
          })
          break
        case 'approval_required':
          callbacks.onApprovalRequired(data as ApprovalRequiredEvent)
          break
        case 'title':
          callbacks.onTitle(data?.title ?? '')
          break
        case 'done':
          callbacks.onDone()
          break
        case 'error':
          callbacks.onError(data?.detail ?? data)
          break
        default:
          break
      }
    })
    await api.post(url, body, { onDownloadProgress: handler.onDownloadProgress })
    handler.flush()
  } catch (e) {
    callbacks.onError(e)
  }
}
