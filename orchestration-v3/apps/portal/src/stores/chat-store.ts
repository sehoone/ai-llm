import { create } from 'zustand';
import type { ApprovalRequiredData, ChatMessage, ChatSession } from '@/api/chat';

export interface PendingApproval extends ApprovalRequiredData {
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
  selectedModelId: number | null; // null = 기본 모델
  selectedRagGroup: string | null; // null = RAG 미사용

  setSessions: (s: ChatSession[]) => void;
  setActiveId: (id: number | null) => void;
  setMessages: (m: ChatMessage[]) => void;
  setMessagesLoading: (b: boolean) => void;
  setSending: (b: boolean) => void;
  setPendingApproval: (p: PendingApproval | null) => void;
  setSelectedModelId: (id: number | null) => void;
  setSelectedRagGroup: (group: string | null) => void;

  appendMessages: (...m: ChatMessage[]) => void;
  updateLastContent: (updater: (prev: string) => string) => void;
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
  selectedModelId: null,
  selectedRagGroup: null,

  setSessions: (sessions) => set({ sessions }),
  setActiveId: (activeId) => set({ activeId }),
  setMessages: (messages) => set({ messages }),
  setMessagesLoading: (messagesLoading) => set({ messagesLoading }),
  setSending: (sending) => set({ sending }),
  setPendingApproval: (pendingApproval) => set({ pendingApproval }),
  setSelectedModelId: (selectedModelId) => set({ selectedModelId }),
  setSelectedRagGroup: (selectedRagGroup) => set({ selectedRagGroup }),

  appendMessages: (...m) => set((s) => ({ messages: [...s.messages, ...m] })),
  updateLastContent: (updater) =>
    set((s) => {
      if (s.messages.length === 0) return s;
      const next = s.messages.slice();
      const last = next[next.length - 1];
      next[next.length - 1] = { ...last, content: updater(last.content) };
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
