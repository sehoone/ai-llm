import { create } from 'zustand';
import type {
  ApprovalRequiredData,
  ChatMessage,
  ChatSession,
  ClarificationRequiredData,
} from '@/api/chat';

export interface PendingApproval extends ApprovalRequiredData {
  sessionId: number;
}

// 되묻기 대기(ADR-0025) — ask_user interrupt를 받으면 설정, 응답 제출 시 클리어.
export interface PendingClarification extends ClarificationRequiredData {
  sessionId: number;
}

// 챗 화면 상태(세션 목록·활성 세션·메시지·전송중). 오케스트레이션은 hooks/use-chat.ts.
interface ChatStore {
  sessions: ChatSession[];
  activeId: number | null;
  messages: ChatMessage[];
  messagesLoading: boolean;
  sending: boolean;
  pendingApproval: PendingApproval | null;
  pendingClarification: PendingClarification | null; // 되묻기 대기 — ADR-0025
  selectedModelId: number | null; // null = 기본 모델
  selectedRagGroup: string | null; // null = RAG 미사용
  selectedSkillIds: string[]; // 활성 스킬(지침 프리셋) — ADR-0024
  activeProjectId: string | null; // 새 대화가 소속될 프로젝트 — ADR-0021

  setSessions: (s: ChatSession[]) => void;
  setActiveId: (id: number | null) => void;
  setMessages: (m: ChatMessage[]) => void;
  setMessagesLoading: (b: boolean) => void;
  setSending: (b: boolean) => void;
  setPendingApproval: (p: PendingApproval | null) => void;
  setPendingClarification: (p: PendingClarification | null) => void;
  setSelectedModelId: (id: number | null) => void;
  setSelectedRagGroup: (group: string | null) => void;
  setSelectedSkillIds: (ids: string[]) => void;
  setActiveProjectId: (id: string | null) => void;

  appendMessages: (...m: ChatMessage[]) => void;
  updateLastContent: (updater: (prev: string) => string) => void;
  markLastAssistantAborted: () => void;
  dropLastAssistant: () => void;

  upsertSessionFront: (s: ChatSession) => void;
  patchSessionTitle: (id: number, title: string) => void;
  removeSession: (id: number) => void;
}

export const useChatStore = create<ChatStore>((set) => ({
  sessions: [],
  activeId: null,
  messages: [],
  messagesLoading: false,
  sending: false,
  pendingApproval: null,
  pendingClarification: null,
  selectedModelId: null,
  selectedRagGroup: null,
  selectedSkillIds: [],
  activeProjectId: null,

  setSessions: (sessions) => set({ sessions }),
  setActiveId: (activeId) => set({ activeId }),
  setMessages: (messages) => set({ messages }),
  setMessagesLoading: (messagesLoading) => set({ messagesLoading }),
  setSending: (sending) => set({ sending }),
  setPendingApproval: (pendingApproval) => set({ pendingApproval }),
  setPendingClarification: (pendingClarification) => set({ pendingClarification }),
  setSelectedModelId: (selectedModelId) => set({ selectedModelId }),
  setSelectedRagGroup: (selectedRagGroup) => set({ selectedRagGroup }),
  setSelectedSkillIds: (selectedSkillIds) => set({ selectedSkillIds }),
  setActiveProjectId: (activeProjectId) => set({ activeProjectId }),

  appendMessages: (...m) => set((s) => ({ messages: [...s.messages, ...m] })),
  updateLastContent: (updater) =>
    set((s) => {
      if (s.messages.length === 0) return s;
      const next = s.messages.slice();
      const last = next[next.length - 1];
      next[next.length - 1] = { ...last, content: updater(last.content) };
      return { messages: next };
    }),
  // 중단(ADR-0025 §5): 마지막 assistant 버블을 aborted로 표시(부분 응답 보존 + "중단됨" 배지).
  // 내용이 비어 있으면(아무 토큰도 안 옴) 빈 버블을 제거한다.
  markLastAssistantAborted: () =>
    set((s) => {
      const next = s.messages.slice();
      const last = next[next.length - 1];
      if (!last || last.role !== 'assistant') return s;
      if (!last.content) {
        next.pop();
      } else {
        next[next.length - 1] = { ...last, status: 'aborted' };
      }
      return { messages: next };
    }),
  dropLastAssistant: () =>
    set((s) => {
      const next = s.messages.slice();
      if (next.length && next[next.length - 1].role === 'assistant') next.pop();
      return { messages: next };
    }),

  upsertSessionFront: (sess) =>
    set((s) => ({ sessions: [sess, ...s.sessions.filter((x) => x.id !== sess.id)] })),
  patchSessionTitle: (id, title) =>
    set((s) => ({ sessions: s.sessions.map((x) => (x.id === id ? { ...x, title } : x)) })),
  removeSession: (id) =>
    set((s) => ({
      sessions: s.sessions.filter((x) => x.id !== id),
      ...(s.activeId === id ? { activeId: null, messages: [] } : {}),
    })),
}));
