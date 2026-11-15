'use client';

import { Markdown } from '@/components/markdown';
import { MessageActions } from '@/components/chat/message-actions';
import { TypingIndicator } from '@/components/chat/typing-indicator';
import type { ChatMessage } from '@/api/chat';

export function MessageBubble({
  message,
  streaming,
  showActions,
  onRegenerate,
}: {
  message: ChatMessage;
  streaming: boolean;
  showActions: boolean;
  onRegenerate?: () => void;
}) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-2xl bg-primary px-4 py-2 text-sm whitespace-pre-wrap text-primary-foreground">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="group/msg flex justify-start">
      <div className="w-full max-w-[80%]">
        {message.content ? (
          <Markdown content={message.content} />
        ) : streaming ? (
          <TypingIndicator />
        ) : null}
        {showActions && <MessageActions content={message.content} onRegenerate={onRegenerate} />}
      </div>
    </div>
  );
}
