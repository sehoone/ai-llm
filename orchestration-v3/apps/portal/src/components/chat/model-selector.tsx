'use client';

import * as React from 'react';
import { ChevronDown, Cpu } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { llmResourceApi, type ChatModel } from '@/api/llm-resources';
import { useChatStore } from '@/stores/chat-store';

// 모델 선택 (ADR-0010) — 활성 chat 리소스 중 선택, 미선택이면 기본 모델.
export function ModelSelector() {
  const [models, setModels] = React.useState<ChatModel[]>([]);
  const selectedModelId = useChatStore((s) => s.selectedModelId);
  const setSelectedModelId = useChatStore((s) => s.setSelectedModelId);
  const sending = useChatStore((s) => s.sending);

  React.useEffect(() => {
    llmResourceApi.chatModels().then(setModels).catch(() => {});
  }, []);

  if (models.length === 0) return null;

  const current = models.find((m) => m.id === selectedModelId);
  const label = current ? current.model_name || current.name : '기본 모델';

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          disabled={sending}
          className="flex h-8 items-center gap-1 rounded-md px-2 text-xs text-muted-foreground transition hover:bg-accent disabled:opacity-50"
        >
          <Cpu className="size-3.5" />
          <span className="max-w-[120px] truncate">{label}</span>
          <ChevronDown className="size-3.5" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="max-h-72 overflow-y-auto">
        <DropdownMenuItem onClick={() => setSelectedModelId(null)}>기본 모델</DropdownMenuItem>
        {models.map((m) => (
          <DropdownMenuItem key={m.id} onClick={() => setSelectedModelId(m.id)}>
            {m.model_name || m.name}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
