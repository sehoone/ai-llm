'use client';

import * as React from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  ChevronsUpDown,
  FolderKanban,
  LogOut,
  MessageSquare,
  PanelLeft,
  Plus,
  Search,
  Settings,
  Sparkles,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
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
import { ConversationItem } from '@/components/chat/conversation-item';
import { useChatStore } from '@/stores/chat-store';
import { useAuthStore } from '@/stores/auth-store';
import { useSettingsStore } from '@/stores/settings-store';
import { type ChatSession } from '@/api/chat';
import { projectsApi } from '@/api/projects';

const NAV = [
  { href: '/projects', label: '프로젝트', icon: FolderKanban },
  { href: '/chat', label: '채팅', icon: MessageSquare },
];

export function ChatSidebar({
  onSelect,
  onNewChat,
  onRename,
  onRemove,
  onNavigate,
  onToggleCollapse,
}: {
  onSelect: (id: number) => void;
  onNewChat: () => void;
  onRename: (id: number, title: string) => void;
  onRemove: (id: number) => void;
  onNavigate?: () => void;
  onToggleCollapse?: () => void;
}) {
  const sessions = useChatStore((s) => s.sessions);
  const activeId = useChatStore((s) => s.activeId);
  const { auth } = useAuthStore();
  const openSettings = useSettingsStore((s) => s.setOpen);
  const router = useRouter();
  const pathname = usePathname();

  const [q, setQ] = React.useState('');
  const [deleteTarget, setDeleteTarget] = React.useState<ChatSession | null>(null);
  // 프로젝트 메타(id→이름·색) — 대화 항목에 배지로 일반 대화와 구분 (ADR-0021).
  const [projectMeta, setProjectMeta] = React.useState<Record<string, { name: string; color: string }>>({});

  React.useEffect(() => {
    projectsApi
      .list()
      .then((ps) =>
        setProjectMeta(Object.fromEntries(ps.map((p) => [p.id, { name: p.name, color: p.color }])))
      )
      .catch(() => {});
  }, []);

  const filtered = q.trim()
    ? sessions.filter((s) => (s.title || '').toLowerCase().includes(q.toLowerCase()))
    : sessions;

  // 계층 구성(ADR-0021): 프로젝트 소속 대화는 프로젝트별로 묶고, 나머지는 일반("최근 대화").
  // 세션은 백엔드에서 최신순 → 그룹 순서도 최근 활동 프로젝트가 위로 온다.
  const generalSessions = filtered.filter((s) => !s.project_id);
  const projectOrder: string[] = [];
  const byProject: Record<string, ChatSession[]> = {};
  for (const s of filtered) {
    if (!s.project_id) continue;
    if (!byProject[s.project_id]) {
      byProject[s.project_id] = [];
      projectOrder.push(s.project_id);
    }
    byProject[s.project_id].push(s);
  }

  const name = auth.user?.username || auth.user?.email || '사용자';
  const email = auth.user?.email ?? '';
  const initial = name.trim().charAt(0).toUpperCase() || '?';

  function logout() {
    auth.reset();
    router.replace('/login');
  }

  return (
    <div className="flex h-full w-full flex-col bg-sidebar text-sidebar-foreground">
      <div className="flex items-center gap-1 px-2 pt-3">
        {onToggleCollapse && (
          <Button
            variant="ghost"
            size="icon"
            className="size-8 shrink-0 text-muted-foreground"
            onClick={onToggleCollapse}
            aria-label="사이드바 접기"
          >
            <PanelLeft className="size-4" />
          </Button>
        )}
        <Link
          href="/"
          onClick={onNavigate}
          className="flex min-w-0 items-center gap-2 rounded-md px-1.5 py-1 font-semibold hover:bg-accent"
        >
          <span className="flex size-6 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <Sparkles className="size-3.5" />
          </span>
          <span className="truncate">AI 포털</span>
        </Link>
      </div>

      <div className="px-3 pb-3 pt-2">
        <Button
          variant="outline"
          className="w-full justify-start"
          onClick={() => {
            onNewChat();
            onNavigate?.();
          }}
        >
          <Plus /> 새 대화
        </Button>
      </div>

      <div className="space-y-1 px-2 pb-2">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              onClick={onNavigate}
              className={cn(
                'flex items-center gap-2 rounded-md px-3 py-2 text-sm',
                active
                  ? 'bg-accent text-accent-foreground'
                  : 'hover:bg-accent hover:text-accent-foreground'
              )}
            >
              <Icon className="size-4" /> {label}
            </Link>
          );
        })}
      </div>

      <div className="px-3 pb-2">
        <div className="relative">
          <Search className="pointer-events-none absolute start-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="대화 검색"
            className="ps-8"
          />
        </div>
      </div>

      <nav className="flex-1 space-y-4 overflow-y-auto px-2 pb-2 pt-1">
        {/* 프로젝트별 그룹 — 헤더 + 들여쓴 대화 목록(계층) */}
        {projectOrder.map((pid) => {
          const meta = projectMeta[pid];
          const projActive = pathname === `/projects/${pid}`;
          return (
            <div key={pid}>
              <Link
                href={`/projects/${pid}`}
                onClick={onNavigate}
                className={cn(
                  'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium',
                  projActive ? 'bg-accent text-accent-foreground' : 'hover:bg-accent'
                )}
              >
                <FolderKanban className="size-3.5 shrink-0" style={{ color: meta?.color }} />
                <span className="truncate">{meta?.name || '프로젝트'}</span>
              </Link>
              <div className="ms-3 mt-1 space-y-1 border-s border-sidebar-border ps-1.5">
                {byProject[pid].map((s) => (
                  <ConversationItem
                    key={s.id}
                    session={s}
                    active={s.id === activeId}
                    onSelect={() => {
                      onSelect(s.id);
                      onNavigate?.();
                    }}
                    onRename={onRename}
                    onRequestDelete={setDeleteTarget}
                  />
                ))}
              </div>
            </div>
          );
        })}

        {/* 일반 대화 */}
        {generalSessions.length > 0 && (
          <div>
            <div className="px-3 pb-1 text-xs font-medium text-muted-foreground">최근 대화</div>
            <div className="space-y-1">
              {generalSessions.map((s) => (
                <ConversationItem
                  key={s.id}
                  session={s}
                  active={s.id === activeId}
                  onSelect={() => {
                    onSelect(s.id);
                    onNavigate?.();
                  }}
                  onRename={onRename}
                  onRequestDelete={setDeleteTarget}
                />
              ))}
            </div>
          </div>
        )}

        {filtered.length === 0 && (
          <p className="px-3 py-2 text-xs text-muted-foreground">
            {q.trim() ? '검색 결과가 없습니다.' : '아직 대화가 없습니다.'}
          </p>
        )}
      </nav>

      <div className="border-t border-sidebar-border p-2">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              className="group flex w-full items-center gap-2.5 rounded-md border border-transparent px-2 py-2 text-sm transition-colors hover:border-sidebar-border hover:bg-accent hover:text-accent-foreground data-[state=open]:border-sidebar-border data-[state=open]:bg-accent"
              aria-label="계정 메뉴 열기"
            >
              <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-medium text-primary-foreground">
                {initial}
              </span>
              <span className="flex min-w-0 flex-1 flex-col text-start leading-tight">
                <span className="truncate font-medium">{name}</span>
                {email && email !== name && (
                  <span className="truncate text-xs text-muted-foreground">{email}</span>
                )}
              </span>
              <ChevronsUpDown className="size-4 shrink-0 text-muted-foreground transition-colors group-hover:text-foreground" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-56">
            <DropdownMenuLabel className="truncate">{name}</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={() => {
                openSettings(true);
                onNavigate?.();
              }}
            >
              <Settings /> 설정
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem variant="destructive" onClick={logout}>
              <LogOut /> 로그아웃
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <AlertDialog open={deleteTarget !== null} onOpenChange={(o) => !o && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>대화를 삭제할까요?</AlertDialogTitle>
            <AlertDialogDescription>
              &ldquo;{deleteTarget?.title || '새 대화'}&rdquo; 대화와 메시지가 영구 삭제됩니다. 되돌릴 수 없습니다.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>취소</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                if (deleteTarget) onRemove(deleteTarget.id);
                setDeleteTarget(null);
              }}
            >
              삭제
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
