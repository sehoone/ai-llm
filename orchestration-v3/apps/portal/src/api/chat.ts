import api from './axios';
import { readSSE } from '@/lib/sse';
import { useAuthStore } from '@/stores/auth-store';

// v3 chat 도메인 (ADR-0008·0011). JSON 엔드포인트는 axios(언랩·Bearer·401), 스트리밍은 fetch.
// 포털 v1은 단순 Q/A 중심 — HITL 승인·첨부·아티팩트는 미지원(관리자 화면에서 처리).
const BASE = 'v1/chat';

export interface ChatSession {
  id: number;
  title: string;
}

export interface ChatMessage {
  id: number;
  role: string; // 'user' | 'assistant' | 'tool'
  content: string;
}

export const chatApi = {
  listSessions: async (): Promise<ChatSession[]> => (await api.get<ChatSession[]>(`${BASE}/sessions`)).data,
  createSession: async (title?: string): Promise<ChatSession> =>
    (await api.post<ChatSession>(`${BASE}/sessions`, { title })).data,
  renameSession: async (id: number, title: string): Promise<ChatSession> =>
    (await api.patch<ChatSession>(`${BASE}/sessions/${id}`, { title })).data,
  deleteSession: async (id: number): Promise<void> => {
    await api.delete(`${BASE}/sessions/${id}`);
  },
  getMessages: async (id: number): Promise<ChatMessage[]> =>
    (await api.get<ChatMessage[]>(`${BASE}/sessions/${id}/messages`)).data,
};

export interface StreamCallbacks {
  onDelta: (text: string) => void;
  onTitle?: (title: string) => void;
  onApprovalRequired?: () => void;
  onError?: (detail: string) => void;
  onAborted?: () => void;
  onDone?: () => void;
}

/** 공통 SSE 구동(fetch). fetch는 axios 인터셉터를 안 타므로 Bearer를 직접 첨부, AbortSignal로 중단. */
async function runStream(
  path: string,
  body: unknown,
  cb: StreamCallbacks,
  signal?: AbortSignal
): Promise<void> {
  const token = useAuthStore.getState().auth.accessToken;
  const base = process.env.NEXT_PUBLIC_API_URL || '';
  try {
    const res = await fetch(`${base}/api/${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
      signal,
    });
    if (res.status === 401) {
      cb.onError?.('인증이 만료되었습니다. 다시 로그인하세요.');
      return;
    }
    if (!res.ok || !res.body) {
      cb.onError?.('요청에 실패했습니다.');
      return;
    }
    await readSSE(res, (event, data) => {
      const d = (data ?? {}) as Record<string, unknown>;
      switch (event) {
        case 'content':
          cb.onDelta(String(d.delta ?? ''));
          break;
        case 'title':
          cb.onTitle?.(String(d.title ?? ''));
          break;
        case 'approval_required':
          cb.onApprovalRequired?.();
          break;
        case 'error':
          cb.onError?.(String(d.detail ?? '오류가 발생했습니다.'));
          break;
        case 'done':
          cb.onDone?.();
          break;
        default:
          break;
      }
    });
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') {
      cb.onAborted?.();
      return;
    }
    cb.onError?.('네트워크 오류가 발생했습니다.');
  }
}

/** 메시지 전송 + 토큰 스트리밍(SSE). */
export async function streamMessage(
  sessionId: number,
  content: string,
  cb: StreamCallbacks,
  signal?: AbortSignal
): Promise<void> {
  await runStream(`${BASE}/sessions/${sessionId}/messages`, { content }, cb, signal);
}

/** 마지막 답변 재생성(SSE) — 직전 assistant 턴 교체(ADR-0020 / portal-roadmap Phase 1). */
export async function regenerate(
  sessionId: number,
  cb: StreamCallbacks,
  signal?: AbortSignal,
  llmResourceId?: number
): Promise<void> {
  await runStream(`${BASE}/sessions/${sessionId}/regenerate`, { llm_resource_id: llmResourceId }, cb, signal);
}
