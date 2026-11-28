'use client';

import * as React from 'react';
import { FolderKanban, MoreHorizontal, Pencil, Plus, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { useChat } from '@/hooks/use-chat';
import { useChatStore } from '@/stores/chat-store';
import { projectsApi } from '@/api/projects';

// 공통 AppHeader 슬롯에 주입되는 chat 전용 조각(ADR-0020). 제목(동적 대화명·프로젝트 배지·인라인
// 이름변경·삭제)과 우측 액션(새 대화)을 분리해 chat/page.tsx가 usePageHeader로 올린다. 펼치기/
// 햄버거 등 네비 토글은 AppHeader가 전역으로 처리하므로 여기선 다루지 않는다.

/** 제목 슬롯 — 프로젝트 배지 + 대화명(인라인 편집) + ⋯ 메뉴(이름변경·삭제). */
export function ChatHeaderTitle() {
  const { rename, remove } = useChat();
  const activeId = useChatStore((s) => s.activeId);
  const sessions = useChatStore((s) => s.sessions);

  const active = sessions.find((s) => s.id === activeId) ?? null;
  const title = active?.title || '새 대화';

  // 프로젝트 배지(ADR-0021) — 활성 대화가 프로젝트 소속이면 이름·색을 표시.
  const [projectMeta, setProjectMeta] = React.useState<
    Record<string, { name: string; color: string }>
  >({});
  React.useEffect(() => {
    projectsApi
      .list()
      .then((ps) =>
        setProjectMeta(Object.fromEntries(ps.map((p) => [p.id, { name: p.name, color: p.color }])))
      )
      .catch(() => {});
  }, []);
  const project = active?.project_id ? projectMeta[active.project_id] : undefined;

  const [editing, setEditing] = React.useState(false);
  const [draft, setDraft] = React.useState('');
  const [deleting, setDeleting] = React.useState(false);

  function startRename() {
    if (!active) return;
    setDraft(active.title);
    setEditing(true);
  }
  function commitRename() {
    setEditing(false);
    if (!active) return;
    const t = draft.trim();
    if (t && t !== active.title) rename(active.id, t);
  }

  return (
    <>
      {project && (
        <span className="flex shrink-0 items-center gap-1 text-muted-foreground">
          <FolderKanban className="size-4" style={{ color: project.color }} />
          <span className="max-w-[160px] truncate">{project.name}</span>
          <span className="text-border">·</span>
        </span>
      )}
      {editing ? (
        <Input
          autoFocus
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commitRename}
          onKeyDown={(e) => {
            if (e.key === 'Enter') commitRename();
            else if (e.key === 'Escape') setEditing(false);
          }}
          className="h-8 max-w-sm"
        />
      ) : (
        <span className="truncate" title={title}>
          {title}
        </span>
      )}

      {active && (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="size-7 shrink-0 text-muted-foreground"
              aria-label="대화 메뉴"
            >
              <MoreHorizontal className="size-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start">
            <DropdownMenuItem onClick={startRename}>
              <Pencil /> 이름 변경
            </DropdownMenuItem>
            <DropdownMenuItem variant="destructive" onClick={() => setDeleting(true)}>
              <Trash2 /> 삭제
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      )}

      <AlertDialog open={deleting} onOpenChange={setDeleting}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>대화를 삭제할까요?</AlertDialogTitle>
            <AlertDialogDescription>
              &ldquo;{active?.title || '새 대화'}&rdquo; 대화와 메시지가 영구 삭제됩니다. 되돌릴 수
              없습니다.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>취소</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                if (active) remove(active.id);
                setDeleting(false);
              }}
            >
              삭제
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}

/** 액션 슬롯 — 새 대화(사이드바와 동일: 일반 대화이므로 프로젝트 스코프 해제, ADR-0021). */
export function ChatHeaderActions() {
  const { newChat } = useChat();
  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={() => {
        useChatStore.getState().setActiveProjectId(null);
        newChat();
      }}
    >
      <Plus className="size-4" /> 새 대화
    </Button>
  );
}
