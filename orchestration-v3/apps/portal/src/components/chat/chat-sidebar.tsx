'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { Bot, BrainCircuit, LogOut, Plus, Search, Settings, User } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ThemeToggle } from '@/components/theme-toggle';
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
import { chatApi, type ChatSession } from '@/api/chat';

export function ChatSidebar({
  onSelect,
  onNewChat,
  onRename,
  onRemove,
  onNavigate,
}: {
  onSelect: (id: number) => void;
  onNewChat: () => void;
  onRename: (id: number, title: string) => void;
  onRemove: (id: number) => void;
  onNavigate?: () => void;
}) {
  const sessions = useChatStore((s) => s.sessions);
  const activeId = useChatStore((s) => s.activeId);
  const { auth } = useAuthStore();
  const router = useRouter();

  const [q, setQ] = React.useState('');
  const [deleteTarget, setDeleteTarget] = React.useState<ChatSession | null>(null);
  const [memoryConfirm, setMemoryConfirm] = React.useState(false);

  async function clearMemory() {
    try {
      await chatApi.deleteMemory();
      toast.success('장기 메모리를 삭제했습니다.');
    } catch {
      toast.error('메모리 삭제에 실패했습니다.');
    }
  }

  const filtered = q.trim()
    ? sessions.filter((s) => (s.title || '').toLowerCase().includes(q.toLowerCase()))
    : sessions;

  const name = auth.user?.username || auth.user?.email || '사용자';

  function logout() {
    auth.reset();
    router.replace('/login');
  }

  return (
    <div className="flex h-full w-full flex-col bg-sidebar text-sidebar-foreground">
      <div className="flex items-center gap-2 p-3">
        <Button
          variant="outline"
          className="flex-1 justify-start"
          onClick={() => {
            onNewChat();
            onNavigate?.();
          }}
        >
          <Plus /> 새 대화
        </Button>
        <ThemeToggle />
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

      <div className="px-2 pb-2">
        <a
          href="/gpts"
          className="flex items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-accent hover:text-accent-foreground"
        >
          <Bot className="size-4" /> 커스텀 GPT
        </a>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-2 pb-2">
        {filtered.map((s) => (
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
        {filtered.length === 0 && (
          <p className="px-3 py-2 text-xs text-muted-foreground">
            {q.trim() ? '검색 결과가 없습니다.' : '아직 대화가 없습니다.'}
          </p>
        )}
      </nav>

      <div className="border-t border-sidebar-border p-2">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-accent hover:text-accent-foreground">
              <User className="size-4" />
              <span className="flex-1 truncate text-start">{name}</span>
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-56">
            <DropdownMenuLabel className="truncate">{name}</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => router.push('/settings')}>
              <Settings /> 설정
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setMemoryConfirm(true)}>
              <BrainCircuit /> 장기 메모리 삭제
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

      <AlertDialog open={memoryConfirm} onOpenChange={setMemoryConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>장기 메모리를 삭제할까요?</AlertDialogTitle>
            <AlertDialogDescription>
              이 사용자에 대해 저장된 모든 장기 메모리가 영구 삭제됩니다. 되돌릴 수 없습니다.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>취소</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                clearMemory();
                setMemoryConfirm(false);
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
