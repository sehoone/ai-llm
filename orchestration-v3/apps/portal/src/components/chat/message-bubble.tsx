'use client';

import { toast } from 'sonner';
import { Download, FileText, Image as ImageIcon } from 'lucide-react';
import { Markdown } from '@/components/markdown';
import { MessageActions } from '@/components/chat/message-actions';
import { TypingIndicator } from '@/components/chat/typing-indicator';
import { chatApi, type AttachmentMeta, type ChatMessage } from '@/api/chat';
import { formatSize, isImageType } from '@/lib/files';

function Attachments({ items, alignEnd }: { items: AttachmentMeta[]; alignEnd?: boolean }) {
  async function download(a: AttachmentMeta) {
    if (a.id == null) return;
    try {
      await chatApi.downloadAttachment(a.id, a.filename);
    } catch {
      toast.error('첨부를 다운로드하지 못했습니다.');
    }
  }
  return (
    <div className={`flex flex-wrap gap-2 ${alignEnd ? 'justify-end' : ''}`}>
      {items.map((a, i) => {
        const clickable = a.id != null;
        return (
          <button
            key={a.id ?? i}
            type="button"
            disabled={!clickable}
            onClick={() => download(a)}
            title={clickable ? '다운로드' : a.filename}
            className="flex items-center gap-2 rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs transition enabled:hover:bg-accent disabled:cursor-default"
          >
            {isImageType(a.content_type) ? (
              <ImageIcon className="size-4 shrink-0 text-muted-foreground" />
            ) : (
              <FileText className="size-4 shrink-0 text-muted-foreground" />
            )}
            <span className="max-w-[160px] truncate">{a.filename}</span>
            <span className="text-muted-foreground">{formatSize(a.file_size)}</span>
            {clickable && <Download className="size-3.5 shrink-0 text-muted-foreground" />}
          </button>
        );
      })}
    </div>
  );
}

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
  const attachments = message.attachments ?? undefined;

  if (message.role === 'user') {
    return (
      <div className="flex flex-col items-end gap-1.5">
        {attachments && attachments.length > 0 && <Attachments items={attachments} alignEnd />}
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
        {attachments && attachments.length > 0 && (
          <div className="mt-2">
            <Attachments items={attachments} />
          </div>
        )}
        {showActions && <MessageActions content={message.content} onRegenerate={onRegenerate} />}
      </div>
    </div>
  );
}
