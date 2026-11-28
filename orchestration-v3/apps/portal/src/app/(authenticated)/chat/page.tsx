'use client';

import * as React from 'react';
import { ChatHeaderActions, ChatHeaderTitle } from '@/components/chat/header-slot';
import { ChatMessages } from '@/components/chat/chat-messages';
import { Composer } from '@/components/chat/composer';
import { ArtifactPanel } from '@/components/chat/artifact-panel';
import { usePageHeader } from '@/hooks/use-page-header';
import { useChat } from '@/hooks/use-chat';
import { useArtifactStore } from '@/stores/artifact-store';

export default function ChatPage() {
  const { newChat, send, regenerate, stop, submitApproval, submitClarification } = useChat();
  const panelOpen = useArtifactStore((s) => s.panelOpen);
  const [draft, setDraft] = React.useState('');
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);

  // 단축키: ⌘/Ctrl+K → 새 대화 + 입력창 포커스
  React.useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        newChat();
        setDraft('');
        textareaRef.current?.focus();
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [newChat]);

  function handleSubmit(files: File[] = []) {
    const t = draft.trim();
    if (!t && files.length === 0) return;
    setDraft('');
    void send(t, files);
  }

  function pickPrompt(p: string) {
    setDraft(p);
    textareaRef.current?.focus();
  }

  // 공통 AppHeader에 chat 슬롯(동적 제목·새 대화) 주입. 조각은 스스로 chat-store를 구독하므로 deps 불필요.
  usePageHeader({ title: <ChatHeaderTitle />, actions: <ChatHeaderActions /> }, []);

  // 셸이 사이드바·헤더를 담당. 여기선 본문(메시지+입력) + 아티팩트 패널만.
  return (
    <div className="flex min-h-0 flex-1">
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <ChatMessages
          onRegenerate={regenerate}
          onPickPrompt={pickPrompt}
          onApprovalDecision={submitApproval}
          onClarify={submitClarification}
        />
        <Composer
          value={draft}
          onChange={setDraft}
          onSubmit={handleSubmit}
          onStop={stop}
          textareaRef={textareaRef}
        />
      </div>

      {panelOpen && <ArtifactPanel />}
    </div>
  );
}
