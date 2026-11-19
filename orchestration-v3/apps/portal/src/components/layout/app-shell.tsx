'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { Menu } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from '@/components/ui/sheet';
import { ChatSidebar } from '@/components/chat/chat-sidebar';
import { useChat } from '@/hooks/use-chat';

// 인증 구역 공통 앱 셸(ADR-0020 포털). claude.ai식 고정 사이드바 — 모든 화면에서 유지되고
// 본문(children)만 교체. 세션 목록 로드·사이드바 콜백은 여기서 전역 스토어(use-chat)로 연결한다.
export function AppShell({ children }: { children: React.ReactNode }) {
  const { loadSessions, selectSession, newChat, rename, remove } = useChat();
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = React.useState(false);

  React.useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  // 챗 외 화면(아티팩트·설정)에서 대화를 선택/새로 시작하면 챗으로 이동시킨다.
  function selectAndGo(id: number) {
    selectSession(id);
    router.push('/chat');
  }
  function newAndGo() {
    newChat();
    router.push('/chat');
  }

  const sidebar = (onNavigate?: () => void) => (
    <ChatSidebar
      onSelect={selectAndGo}
      onNewChat={newAndGo}
      onRename={rename}
      onRemove={remove}
      onNavigate={onNavigate}
    />
  );

  return (
    <div className="flex h-svh">
      <aside className="hidden w-72 shrink-0 border-e border-sidebar-border md:block">
        {sidebar()}
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-2 border-b border-border p-2 md:hidden">
          <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" aria-label="메뉴 열기">
                <Menu />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-72 p-0">
              <SheetTitle className="sr-only">메뉴</SheetTitle>
              {sidebar(() => setMobileOpen(false))}
            </SheetContent>
          </Sheet>
          <span className="text-sm font-medium">AI 포털</span>
        </header>

        {children}
      </div>
    </div>
  );
}
