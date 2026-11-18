'use client';

import * as React from 'react';
import { ChevronDown, Database } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { ragApi, type RagGroup } from '@/api/rag';
import { useChatStore } from '@/stores/chat-store';

// RAG 지식베이스 선택 (ADR-0012) — 선택 시 rag_group으로 챗에 컨텍스트 사전 주입. 그룹 없으면 미표시.
export function RagSelector() {
  const [groups, setGroups] = React.useState<RagGroup[]>([]);
  const selected = useChatStore((s) => s.selectedRagGroup);
  const setSelected = useChatStore((s) => s.setSelectedRagGroup);
  const sending = useChatStore((s) => s.sending);

  React.useEffect(() => {
    ragApi.listGroups().then(setGroups).catch(() => {});
  }, []);

  if (groups.length === 0) return null;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          disabled={sending}
          className={`flex h-8 items-center gap-1 rounded-md px-2 text-xs transition hover:bg-accent disabled:opacity-50 ${
            selected ? 'text-emerald-600 dark:text-emerald-400' : 'text-muted-foreground'
          }`}
        >
          <Database className="size-3.5" />
          <span className="max-w-[120px] truncate">{selected || '지식베이스'}</span>
          <ChevronDown className="size-3.5" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="max-h-72 overflow-y-auto">
        <DropdownMenuItem onClick={() => setSelected(null)}>사용 안 함</DropdownMenuItem>
        {groups.map((g) => (
          <DropdownMenuItem key={g.id} onClick={() => setSelected(g.name)}>
            {g.name}
            <span className="ms-auto text-xs text-muted-foreground">{g.doc_count}</span>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
