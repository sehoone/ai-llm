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

/** 전송용 첨부 (base64) — ADR-0014 FileAttachment. */
export interface FileAttachment {
  filename: string;
  content_type: string;
  data: string; // base64
}

/** 조회용 첨부 메타 (바이트 미포함). id가 있으면 다운로드 가능. */
export interface AttachmentMeta {
  id?: number;
  filename: string;
  content_type: string;
  file_size: number;
}

export interface ChatMessage {
  id: number;
  role: string; // 'user' | 'assistant' | 'tool'
  content: string;
  attachments?: AttachmentMeta[] | null;
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

  /** 첨부 다운로드 — 소유자/관리자만(ADR-0014 §4). axios가 Bearer 첨부, blob으로 받아 저장. */
  downloadAttachment: async (id: number, filename: string): Promise<void> => {
    const res = await api.get(`${BASE}/attachments/${id}`, { responseType: 'blob' });
    const url = URL.createObjectURL(res.data as Blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },
};

// HITL 승인 (ADR-0008)
export interface ApprovalRequest {
  tool_call_id: string;
  name: string;
  args: Record<string, unknown>;
  tier: string;
  reason?: string | null;
}
export interface ApprovalRequiredData {
  group_key: string;
  requests: ApprovalRequest[];
}
export interface ApprovalDecision {
  tool_call_id: string;
  approved: boolean;
  args?: Record<string, unknown>;
}

export interface StreamCallbacks {
  onDelta: (text: string) => void;
  onTitle?: (title: string) => void;
  onApprovalRequired?: (data: ApprovalRequiredData) => void;
  onError?: (detail: string) => void;
  onAborted?: () => void;
  onDone?: () => void;
  // 아티팩트(ADR-0013) 스트리밍
  onArtifactStart?: (identifier: string, type: string, title: string) => void;
  onArtifactDelta?: (identifier: string, delta: string) => void;
  onArtifactEnd?: (identifier: string, version?: number) => void;
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
          cb.onApprovalRequired?.({
            group_key: String(d.group_key ?? ''),
            requests: Array.isArray(d.requests) ? (d.requests as ApprovalRequest[]) : [],
          });
          break;
        case 'error':
          cb.onError?.(String(d.detail ?? '오류가 발생했습니다.'));
          break;
        case 'done':
          cb.onDone?.();
          break;
        case 'artifact_start':
          cb.onArtifactStart?.(
            String(d.identifier ?? ''),
            String(d.artifact_type ?? 'text/markdown'),
            String(d.title ?? '')
          );
          break;
        case 'artifact_delta':
          cb.onArtifactDelta?.(String(d.identifier ?? ''), String(d.delta ?? ''));
          break;
        case 'artifact_end':
          cb.onArtifactEnd?.(
            String(d.identifier ?? ''),
            typeof d.version === 'number' ? d.version : undefined
          );
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

/** 메시지 전송 + 토큰 스트리밍(SSE). files는 base64 멀티모달 첨부(ADR-0014). */
export async function streamMessage(
  sessionId: number,
  content: string,
  cb: StreamCallbacks,
  signal?: AbortSignal,
  files?: FileAttachment[],
  llmResourceId?: number | null
): Promise<void> {
  const body: Record<string, unknown> = { content };
  if (files && files.length) body.files = files;
  if (llmResourceId != null) body.llm_resource_id = llmResourceId;
  await runStream(`${BASE}/sessions/${sessionId}/messages`, body, cb, signal);
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

/** 승인/거부 결정 제출 → 그래프 재개 스트리밍(SSE) — ADR-0008 §4. */
export async function submitApprovals(
  sessionId: number,
  groupKey: string,
  decisions: ApprovalDecision[],
  cb: StreamCallbacks,
  signal?: AbortSignal
): Promise<void> {
  await runStream(
    `${BASE}/sessions/${sessionId}/approvals`,
    { group_key: groupKey, decisions },
    cb,
    signal
  );
}
