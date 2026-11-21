'use client';

import * as React from 'react';
import { FolderKanban, MoreHorizontal, Pencil, Trash2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Input } from '@/components/ui/input';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import type { ChatSession } from '@/api/chat';

export function ConversationItem({
  session,
  active,
  project,
  onSelect,
  onRename,
  onRequestDelete,
}: {
  session: ChatSession;
  active: boolean;
  // 소속 프로젝트 메타(ADR-0021) — 있으면 일반 대화와 구분되게 배지 표시.
  project?: { name: string; color: string };
  onSelect: () => void;
  onRename: (id: number, title: string) => void;
  onRequestDelete: (session: ChatSession) => void;
}) {
  const [editing, setEditing] = React.useState(false);
  const [draft, setDraft] = React.useState(session.title);

  React.useEffect(() => {
    if (!editing) setDraft(session.title);
  }, [session.title, editing]);

  function commit() {
    setEditing(false);
    const t = draft.trim();
    if (t && t !== session.title) onRename(session.id, t);
  }

  if (editing) {
    return (
      <Input
        autoFocus
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === 'Enter') commit();
          else if (e.key === 'Escape') setEditing(false);
        }}
        className="h-8"
      />
    );
  }

  return (
    <div
      className={cn(
        'group/item flex items-center rounded-md',
        active ? 'bg-accent text-accent-foreground' : 'hover:bg-accent/60'
      )}
    >
      <button
        onClick={onSelect}
        className="min-w-0 flex-1 px-3 py-2 text-start"
        title={session.title || '새 대화'}
      >
        <span className="block truncate text-sm">{session.title || '새 대화'}</span>
        {project && (
          <span className="mt-0.5 flex items-center gap-1 text-xs text-muted-foreground">
            <FolderKanban className="size-3 shrink-0" style={{ color: project.color }} />
            <span className="truncate">{project.name}</span>
          </span>
        )}
      </button>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            className="me-1 rounded p-1 text-muted-foreground opacity-0 transition hover:bg-background/60 group-hover/item:opacity-100 data-[state=open]:opacity-100"
            aria-label="대화 메뉴"
          >
            <MoreHorizontal className="size-4" />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onClick={() => setEditing(true)}>
            <Pencil /> 이름 변경
          </DropdownMenuItem>
          <DropdownMenuItem variant="destructive" onClick={() => onRequestDelete(session)}>
            <Trash2 /> 삭제
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
