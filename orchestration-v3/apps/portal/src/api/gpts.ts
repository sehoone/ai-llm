import api from './axios';
import { readSSE } from '@/lib/sse';
import { useAuthStore } from '@/stores/auth-store';

// 커스텀 GPT 도메인 — 사용자 정의 GPT. 채팅은 단순 Q/A(도구·HITL 없음), V2 SSE `data:{content,done}`.
const BASE = 'v1/gpts';

export interface CustomGpt {
  id: string;
  user_id: number;
  name: string;
  description: string | null;
  instructions: string;
  rag_key: string;
  is_public: boolean;
  model: string;
}

export interface GptSession {
  session_id: string;
  name: string;
  custom_gpt_id: string;
}

export interface GptMessage {
  role: string; // 'user' | 'assistant'
  content: string;
}

export const gptsApi = {
  list: async (): Promise<CustomGpt[]> => (await api.get<CustomGpt[]>(BASE)).data,
  get: async (id: string): Promise<CustomGpt> => (await api.get<CustomGpt>(`${BASE}/${id}`)).data,
  create: async (body: {
    name: string;
    description?: string;
    instructions: string;
  }): Promise<CustomGpt> => (await api.post<CustomGpt>(BASE, body)).data,
  remove: async (id: string): Promise<void> => {
    await api.delete(`${BASE}/${id}`);
  },
  createSession: async (id: string): Promise<GptSession> =>
    (await api.post<GptSession>(`${BASE}/${id}/sessions`, {})).data,
  getMessages: async (id: string, sessionId: string): Promise<GptMessage[]> =>
    (await api.get<{ messages: GptMessage[] }>(`${BASE}/${id}/messages`, {
      params: { session_id: sessionId },
    })).data.messages,
};

export interface GptStreamCallbacks {
  onContent: (text: string) => void;
  onTitle?: (title: string) => void;
  onError?: (detail: string) => void;
  onDone?: () => void;
}

/** GPT 채팅 스트리밍(SSE V2: `data:{content,done,type?,title?}`). */
export async function streamGptChat(
  gptId: string,
  body: { session_id: string; messages: GptMessage[]; llm_resource_id?: number },
  cb: GptStreamCallbacks,
  signal?: AbortSignal
): Promise<void> {
  const token = useAuthStore.getState().auth.accessToken;
  const base = process.env.NEXT_PUBLIC_API_URL || '';
  try {
    const res = await fetch(`${base}/api/${BASE}/${gptId}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
      signal,
    });
    if (!res.ok || !res.body) {
      cb.onError?.('메시지 전송에 실패했습니다.');
      return;
    }
    await readSSE(res, (_event, data) => {
      const d = (data ?? {}) as Record<string, unknown>;
      if (d.type === 'title') {
        cb.onTitle?.(String(d.title ?? ''));
        return;
      }
      if (d.content) cb.onContent(String(d.content));
      if (d.done) cb.onDone?.();
    });
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') return;
    cb.onError?.('네트워크 오류가 발생했습니다.');
  }
}
