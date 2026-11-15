'use client';

import { useCallback, useRef } from 'react';
import { toast } from 'sonner';
import {
  chatApi,
  regenerate as apiRegenerate,
  streamMessage,
  type StreamCallbacks,
} from '@/api/chat';
import { useChatStore } from '@/stores/chat-store';

const APPROVAL_NOTE = '\n\n_(이 작업은 승인이 필요합니다. 현재 포털에서는 지원되지 않습니다.)_';
const FLUSH_MS = 60; // 토큰 반영 throttle — 스트리밍 중 마크다운 재파싱 빈도 제한

const getState = useChatStore.getState;

/** 챗 오케스트레이션: 로드·선택·전송·중단·재생성·이름변경·삭제. 상태는 chat-store. */
export function useChat() {
  const abortRef = useRef<AbortController | null>(null);
  const bufferRef = useRef('');
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const flush = useCallback(() => {
    const buf = bufferRef.current;
    if (!buf) return;
    bufferRef.current = '';
    getState().updateLastContent((prev) => prev + buf);
  }, []);

  const startFlushing = useCallback(() => {
    if (timerRef.current) return;
    timerRef.current = setInterval(flush, FLUSH_MS);
  }, [flush]);

  const stopFlushing = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  /** 스트리밍 1회 구동: throttle 시작 → 콜백 수집 → 종료 시 flush + sending 해제. */
  const drive = useCallback(
    async (
      sessionId: number,
      call: (cb: StreamCallbacks, signal: AbortSignal) => Promise<void>
    ) => {
      const controller = new AbortController();
      abortRef.current = controller;
      startFlushing();
      const cb: StreamCallbacks = {
        onDelta: (t) => {
          bufferRef.current += t;
        },
        onTitle: (title) => getState().patchSessionTitle(sessionId, title),
        onApprovalRequired: () => {
          bufferRef.current += APPROVAL_NOTE;
        },
        onError: (d) => toast.error(d),
      };
      try {
        await call(cb, controller.signal);
      } finally {
        stopFlushing();
        flush();
        abortRef.current = null;
        getState().setSending(false);
      }
    },
    [startFlushing, stopFlushing, flush]
  );

  const loadSessions = useCallback(async () => {
    try {
      getState().setSessions(await chatApi.listSessions());
    } catch {
      toast.error('대화 목록을 불러오지 못했습니다.');
    }
  }, []);

  const selectSession = useCallback(async (id: number) => {
    const st = getState();
    if (st.sending || st.activeId === id) return;
    st.setActiveId(id);
    try {
      st.setMessages(await chatApi.getMessages(id));
    } catch {
      toast.error('메시지를 불러오지 못했습니다.');
    }
  }, []);

  const newChat = useCallback(() => {
    const st = getState();
    if (st.sending) return;
    st.setActiveId(null);
    st.setMessages([]);
  }, []);

  const send = useCallback(
    async (content: string) => {
      const text = content.trim();
      const st = getState();
      if (!text || st.sending) return;
      st.setSending(true);

      let sessionId = st.activeId;
      if (sessionId == null) {
        try {
          const s = await chatApi.createSession();
          sessionId = s.id;
          getState().setActiveId(s.id);
          getState().upsertSessionFront(s);
        } catch {
          toast.error('새 대화를 만들지 못했습니다.');
          getState().setSending(false);
          return;
        }
      }
      if (sessionId == null) {
        getState().setSending(false);
        return;
      }
      const sid = sessionId;

      const uid = Date.now();
      getState().appendMessages(
        { id: uid, role: 'user', content: text },
        { id: uid + 1, role: 'assistant', content: '' }
      );
      await drive(sid, (cb, signal) => streamMessage(sid, text, cb, signal));
    },
    [drive]
  );

  const regenerate = useCallback(async () => {
    const st = getState();
    if (st.activeId == null || st.sending) return;
    const sessionId = st.activeId;
    st.setSending(true);
    getState().dropLastAssistant();
    getState().appendMessages({ id: Date.now(), role: 'assistant', content: '' });
    await drive(sessionId, (cb, signal) => apiRegenerate(sessionId, cb, signal));
  }, [drive]);

  const stop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const rename = useCallback(async (id: number, title: string) => {
    const t = title.trim();
    if (!t) return;
    try {
      await chatApi.renameSession(id, t);
      getState().patchSessionTitle(id, t);
    } catch {
      toast.error('이름을 변경하지 못했습니다.');
    }
  }, []);

  const remove = useCallback(async (id: number) => {
    try {
      await chatApi.deleteSession(id);
      getState().removeSession(id);
    } catch {
      toast.error('대화를 삭제하지 못했습니다.');
    }
  }, []);

  return { loadSessions, selectSession, newChat, send, regenerate, stop, rename, remove };
}
