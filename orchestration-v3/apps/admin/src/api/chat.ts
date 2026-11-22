import api from './axios'
import type {
  AttachmentMeta,
  ChatHistoryListResponse,
  ChatHistoryResponse,
} from '@/types/chat-api'

// v3 chat 도메인 (ADR-0008). 백엔드는 /api/v1/chat/*, 세션 id는 int 기반.
// 대화형 챗·아티팩트 화면은 portal로 이관(ADR-0020) — web(admin)은
// 관리자 대화 이력(chat-history), 첨부 다운로드만 사용한다.
const CHAT_BASE = 'v1/chat'

/** 백엔드 ChatHistoryItem(session_id:int) → web ChatHistoryResponse(session_id:string). */
interface V3HistoryItem extends Omit<ChatHistoryResponse, 'session_id'> {
  session_id: number
}
function toHistoryItem(h: V3HistoryItem): ChatHistoryResponse {
  return { ...h, session_id: String(h.session_id) }
}

export const chatService = {
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
