'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { Menu, PanelLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from '@/components/ui/sheet';
import { ChatSidebar } from '@/components/chat/chat-sidebar';
import { SettingsDialog } from '@/components/settings/settings-dialog';
import { RecordingBar } from '@/components/meeting/recording-bar';
import { SaveRecordingDialog } from '@/components/meeting/save-recording-dialog';
import { useChat } from '@/hooks/use-chat';
import { useChatStore } from '@/stores/chat-store';

// 인증 구역 공통 앱 셸(ADR-0020 포털). claude.ai식 고정 사이드바 — 모든 화면에서 유지되고
// 본문(children)만 교체. 세션 목록 로드·사이드바 콜백은 여기서 전역 스토어(use-chat)로 연결한다.
export function AppShell({ children }: { children: React.ReactNode }) {
  const { loadSessions, selectSession, newChat, rename, remove } = useChat();
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = React.useState(false);
  // 데스크톱 사이드바 접힘 상태(claude.ai식). 접히면 본문 좌상단 플로팅 버튼으로 다시 펼친다.
  const [collapsed, setCollapsed] = React.useState(false);

  React.useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  // 챗 외 화면(아티팩트·설정)에서 대화를 선택/새로 시작하면 챗으로 이동시킨다.
  function selectAndGo(id: number) {
    selectSession(id);
    router.push('/chat');
  }
  function newAndGo() {
    // 사이드바의 새 대화는 일반 대화 — 프로젝트 홈에서 남은 activeProjectId를 비운다 (ADR-0021).
    useChatStore.getState().setActiveProjectId(null);
    newChat();
    router.push('/chat');
  }

  const sidebar = (opts?: { onNavigate?: () => void; onToggleCollapse?: () => void }) => (
    <ChatSidebar
      onSelect={selectAndGo}
      onNewChat={newAndGo}
      onRename={rename}
      onRemove={remove}
      onNavigate={opts?.onNavigate}
      onToggleCollapse={opts?.onToggleCollapse}
    />
  );

  return (
    <div className="flex h-svh">
      {!collapsed && (
        <aside className="hidden w-72 shrink-0 border-e border-sidebar-border md:block">
          {sidebar({ onToggleCollapse: () => setCollapsed(true) })}
        </aside>
      )}

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
              {sidebar({
                onNavigate: () => setMobileOpen(false),
                onToggleCollapse: () => setMobileOpen(false),
              })}
            </SheetContent>
          </Sheet>
          <span className="text-sm font-medium">AI 포털</span>
        </header>

        {children}
      </div>

      {/* 데스크톱: 접힌 상태에서 사이드바를 다시 펼치는 플로팅 버튼 */}
      {collapsed && (
        <Button
          variant="outline"
          size="icon"
          className="fixed start-2 top-2 z-30 hidden size-8 md:flex"
          onClick={() => setCollapsed(false)}
          aria-label="사이드바 펼치기"
        >
          <PanelLeft className="size-4" />
        </Button>
      )}

      <SettingsDialog />
      {/* 전역 녹음 바·저장 다이얼로그 — 메뉴 이동 중에도 녹음 유지 (meeting-minutes) */}
      <RecordingBar />
      <SaveRecordingDialog />
    </div>
  );
}
