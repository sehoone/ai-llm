'use client';

import * as React from 'react';
import { toast } from 'sonner';
import { ArrowUp, FileText, Image as ImageIcon, Paperclip, Square, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { ModelSelector } from '@/components/chat/model-selector';
import { RagSelector } from '@/components/chat/rag-selector';
import { useChatStore } from '@/stores/chat-store';
import { ACCEPT_ATTR, isImageType, validateFile } from '@/lib/files';

export function Composer({
  value,
  onChange,
  onSubmit,
  onStop,
  textareaRef,
}: {
  value: string;
  onChange: (v: string) => void;
  onSubmit: (files: File[]) => void;
  onStop: () => void;
  textareaRef?: React.Ref<HTMLTextAreaElement>;
}) {
  const sending = useChatStore((s) => s.sending);
  const [files, setFiles] = React.useState<File[]>([]);
  const [dragActive, setDragActive] = React.useState(false);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  function addFiles(list: FileList | null) {
    if (!list) return;
    const valid: File[] = [];
    for (const f of Array.from(list)) {
      const err = validateFile(f);
      if (err) toast.error(err);
      else valid.push(f);
    }
    if (valid.length) setFiles((prev) => [...prev, ...valid]);
  }

  function submit() {
    if ((!value.trim() && files.length === 0) || sending) return;
    onSubmit(files);
    setFiles([]);
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  const canSend = sending || value.trim().length > 0 || files.length > 0;

  return (
    <div className="border-t border-border bg-background">
      <div className="mx-auto max-w-3xl p-4">
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragActive(false);
            addFiles(e.dataTransfer.files);
          }}
          className={`rounded-2xl border bg-card shadow-sm transition ${
            dragActive ? 'border-ring ring-2 ring-ring/40' : 'border-input focus-within:border-ring'
          }`}
        >
          {files.length > 0 && (
            <div className="flex flex-wrap gap-2 p-2 pb-0">
              {files.map((f, i) => (
                <div
                  key={`${f.name}-${i}`}
                  className="relative flex items-center gap-2 rounded-md border border-border bg-muted/50 py-1.5 ps-2 pe-6 text-xs"
                >
                  {isImageType(f.type) ? (
                    <ImageIcon className="size-4 shrink-0 text-muted-foreground" />
                  ) : (
                    <FileText className="size-4 shrink-0 text-muted-foreground" />
                  )}
                  <span className="max-w-[160px] truncate" title={f.name}>
                    {f.name}
                  </span>
                  <button
                    type="button"
                    onClick={() => setFiles((prev) => prev.filter((_, idx) => idx !== i))}
                    className="absolute end-1 top-1/2 -translate-y-1/2 rounded-full p-0.5 text-muted-foreground hover:bg-background"
                    aria-label="첨부 제거"
                  >
                    <X className="size-3.5" />
                  </button>
                </div>
              ))}
            </div>
          )}

          <div className="flex items-center gap-1 px-2 pt-1">
            <ModelSelector />
            <RagSelector />
          </div>

          <div className="flex items-end gap-1 p-1 pt-0">
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept={ACCEPT_ATTR}
              className="hidden"
              onChange={(e) => {
                addFiles(e.target.files);
                e.target.value = '';
              }}
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="size-9 shrink-0"
              onClick={() => fileInputRef.current?.click()}
              aria-label="파일 첨부"
            >
              <Paperclip className="size-5" />
            </Button>
            <Textarea
              ref={textareaRef}
              value={value}
              onChange={(e) => onChange(e.target.value)}
              onKeyDown={onKeyDown}
              rows={1}
              placeholder="메시지를 입력하세요 (Enter 전송, Shift+Enter 줄바꿈)"
              className="max-h-48 resize-none border-0 bg-transparent py-2 shadow-none focus-visible:ring-0"
            />
            <Button
              type="button"
              size="icon"
              className="size-9 shrink-0 rounded-full"
              onClick={sending ? onStop : submit}
              disabled={!canSend}
              aria-label={sending ? '중단' : '전송'}
            >
              {sending ? <Square className="size-4" /> : <ArrowUp className="size-4" />}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
