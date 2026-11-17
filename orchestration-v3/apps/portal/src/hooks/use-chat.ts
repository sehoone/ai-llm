'use client';

import { useCallback, useRef } from 'react';
import { toast } from 'sonner';
import {
  chatApi,
  regenerate as apiRegenerate,
  streamMessage,
  type AttachmentMeta,
  type FileAttachment,
  type StreamCallbacks,
} from '@/api/chat';
import { fileToBase64 } from '@/lib/files';
import { artifactApi } from '@/api/artifacts';
import { useChatStore } from '@/stores/chat-store';
import { useArtifactStore } from '@/stores/artifact-store';

const APPROVAL_NOTE = '\n\n_(이 작업은 승인이 필요합니다. 현재 포털에서는 지원되지 않습니다.)_';
const FLUSH_MS = 60; // 토큰 반영 throttle — 스트리밍 중 마크다운 재파싱 빈도 제한

const getState = useChatStore.getState;
const getArt = useArtifactStore.getState;

/** 세션의 아티팩트 요약을 로드해 스토어에 병합(실패는 무시 — 아티팩트는 선택적). */
async function loadArtifacts(sessionId: number): Promise<void> {
  try {
    getArt().mergeSummaries(await artifactApi.listBySession(sessionId));
  } catch {
    /* ignore */
  }
}

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
        // 아티팩트(ADR-0013): 시작 시 패널 자동 오픈, 델타 누적.
        onArtifactStart: (id, type, title) => {
          getArt().startArtifact(id, type, title);
          getArt().openPanel(id);
        },
        onArtifactDelta: (id, delta) => getArt().appendArtifact(id, delta),
        onArtifactEnd: (id, version) => getArt().endArtifact(id, version),
      };
      try {
        await call(cb, controller.signal);
      } finally {
        stopFlushing();
        flush();
        abortRef.current = null;
        getState().setSending(false);
        // 완료 후 정규화: 서버 메시지로 교체해 첨부 id·assistant id를 확정(다운로드 가능).
        // 중단됐거나 그새 다른 세션으로 이동했으면 생략(낙관적 메시지 보존).
        if (!controller.signal.aborted && getState().activeId === sessionId) {
          try {
            getState().setMessages(await chatApi.getMessages(sessionId));
          } catch {
            /* 정규화 실패는 무시 */
          }
          await loadArtifacts(sessionId); // 아티팩트 id·published 확정(publish·지연로드용)
        }
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
    getArt().reset();
    try {
      st.setMessages(await chatApi.getMessages(id));
    } catch {
      toast.error('메시지를 불러오지 못했습니다.');
    }
    void loadArtifacts(id);
  }, []);

  const newChat = useCallback(() => {
    const st = getState();
    if (st.sending) return;
    st.setActiveId(null);
    st.setMessages([]);
    getArt().reset();
  }, []);

  const send = useCallback(
    async (content: string, files: File[] = []) => {
      const text = content.trim();
      const st = getState();
      if ((!text && files.length === 0) || st.sending) return;
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

      // 첨부(ADR-0014): base64 변환 + 낙관적 메타. content는 min_length=1이라 파일만일 때 기본 문구.
      let fileAttachments: FileAttachment[] | undefined;
      let optimistic: AttachmentMeta[] | undefined;
      if (files.length) {
        try {
          fileAttachments = await Promise.all(
            files.map(async (f) => ({
              filename: f.name,
              content_type: f.type || 'application/octet-stream',
              data: await fileToBase64(f),
            }))
          );
        } catch {
          toast.error('첨부 파일을 읽지 못했습니다.');
          getState().setSending(false);
          return;
        }
        optimistic = files.map((f) => ({
          filename: f.name,
          content_type: f.type,
          file_size: f.size,
        }));
      }
      const sendText = text || '첨부한 파일을 확인해줘.';

      const uid = Date.now();
      getState().appendMessages(
        { id: uid, role: 'user', content: sendText, attachments: optimistic },
        { id: uid + 1, role: 'assistant', content: '' }
      );
      await drive(sid, (cb, signal) => streamMessage(sid, sendText, cb, signal, fileAttachments));
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
