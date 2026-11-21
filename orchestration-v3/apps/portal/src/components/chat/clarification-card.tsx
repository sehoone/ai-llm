'use client';

import * as React from 'react';
import { HelpCircle, Send } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useChatStore } from '@/stores/chat-store';
import type { ClarifyAnswer } from '@/api/chat';

// 되묻기 카드 (ADR-0025) — ask_user interrupt 시 질문 + 보기 칩 + 자유입력으로 응답.
export function ClarificationCard({ onSubmit }: { onSubmit: (answer: ClarifyAnswer) => void }) {
  const pending = useChatStore((s) => s.pendingClarification);
  const sending = useChatStore((s) => s.sending);
  const [text, setText] = React.useState('');

  // 되묻기가 바뀌면 입력 초기화.
  React.useEffect(() => {
    setText('');
  }, [pending?.tool_call_id]);

  if (!pending) return null;

  const submitText = () => {
    const t = text.trim();
    if (!t || sending) return;
    onSubmit({ text: t });
  };

  return (
    <div className="rounded-xl border border-sky-300 bg-sky-50 p-3 text-sm dark:border-sky-900/50 dark:bg-sky-950/30">
      <div className="mb-2 flex items-center gap-2 font-medium text-sky-700 dark:text-sky-400">
        <HelpCircle className="size-4" /> 확인이 필요합니다
      </div>
      <p className="mb-3 whitespace-pre-wrap text-foreground">{pending.question}</p>

      {pending.options && pending.options.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-2">
          {pending.options.map((o) => (
            <Button
              key={o.value}
              variant="outline"
              size="sm"
              disabled={sending}
              onClick={() => onSubmit({ value: o.value })}
            >
              {o.label}
            </Button>
          ))}
        </div>
      )}

      {pending.allow_free_text && (
        <form
          className="flex items-center gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            submitText();
          }}
        >
          <Input
            autoFocus
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="답변을 입력하세요…"
            disabled={sending}
          />
          <Button type="submit" size="icon" disabled={sending || !text.trim()}>
            <Send className="size-4" />
          </Button>
        </form>
      )}
    </div>
  );
}
