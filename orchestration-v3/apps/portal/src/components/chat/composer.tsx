'use client';

import * as React from 'react';
import { ArrowUp, Square } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { useChatStore } from '@/stores/chat-store';

export function Composer({
  value,
  onChange,
  onSubmit,
  onStop,
  textareaRef,
}: {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  onStop: () => void;
  textareaRef?: React.Ref<HTMLTextAreaElement>;
}) {
  const sending = useChatStore((s) => s.sending);

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!sending) onSubmit();
    }
  }

  return (
    <div className="border-t border-border bg-background">
      <div className="mx-auto max-w-3xl p-4">
        <div className="relative flex items-end rounded-2xl border border-input bg-card shadow-sm focus-within:border-ring">
          <Textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={onKeyDown}
            rows={1}
            placeholder="메시지를 입력하세요 (Enter 전송, Shift+Enter 줄바꿈)"
            className="max-h-48 resize-none border-0 bg-transparent py-3 pe-12 shadow-none focus-visible:ring-0"
          />
          <Button
            type="button"
            size="icon"
            className="absolute end-2 bottom-2 size-8 rounded-full"
            onClick={sending ? onStop : onSubmit}
            disabled={!sending && !value.trim()}
            aria-label={sending ? '중단' : '전송'}
          >
            {sending ? <Square className="size-4" /> : <ArrowUp className="size-4" />}
          </Button>
        </div>
      </div>
    </div>
  );
}
