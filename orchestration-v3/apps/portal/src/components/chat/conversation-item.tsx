'use client';

import * as React from 'react';
import { MoreHorizontal, Pencil, Trash2 } from 'lucide-react';
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
  onSelect,
  onRename,
  onRequestDelete,
}: {
  session: ChatSession;
  active: boolean;
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
        className="flex-1 truncate px-3 py-2 text-start text-sm"
        title={session.title || '새 대화'}
      >
        {session.title || '새 대화'}
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
