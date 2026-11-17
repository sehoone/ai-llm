'use client';

import * as React from 'react';
import { MessageBubble } from '@/components/chat/message-bubble';
import { EmptyState } from '@/components/chat/empty-state';
import { ApprovalCard } from '@/components/chat/approval-card';
import { useChatStore } from '@/stores/chat-store';

export function ChatMessages({
  onRegenerate,
  onPickPrompt,
  onApprovalDecision,
}: {
  onRegenerate: () => void;
  onPickPrompt: (prompt: string) => void;
  onApprovalDecision: (approved: boolean) => void;
}) {
  const messages = useChatStore((s) => s.messages);
  const sending = useChatStore((s) => s.sending);
  const containerRef = React.useRef<HTMLDivElement>(null);
  const pinnedRef = React.useRef(true); // 사용자가 바닥 근처면 자동 스크롤 유지

  const onScroll = React.useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    pinnedRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 120;
  }, []);

  React.useEffect(() => {
    const el = containerRef.current;
    if (el && pinnedRef.current) el.scrollTop = el.scrollHeight;
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 overflow-y-auto">
        <EmptyState onPick={onPickPrompt} />
      </div>
    );
  }

  const lastIndex = messages.length - 1;
  return (
    <div ref={containerRef} onScroll={onScroll} className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-3xl space-y-5 px-4 py-6">
        {messages.map((m, i) => {
          const isLast = i === lastIndex;
          const streaming = sending && isLast && m.role === 'assistant';
          const showActions = m.role === 'assistant' && !streaming && m.content.length > 0;
          return (
            <MessageBubble
              key={m.id}
              message={m}
              streaming={streaming}
              showActions={showActions}
              onRegenerate={isLast && !sending ? onRegenerate : undefined}
            />
          );
        })}
        <ApprovalCard onDecision={onApprovalDecision} />
      </div>
    </div>
  );
}
