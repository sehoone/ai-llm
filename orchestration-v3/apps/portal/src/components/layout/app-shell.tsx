'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet';
import { AppHeader } from '@/components/layout/app-header';
import { ChatSidebar } from '@/components/chat/chat-sidebar';
import { SettingsDialog } from '@/components/settings/settings-dialog';
import { RecordingBar } from '@/components/meeting/recording-bar';
import { SaveRecordingDialog } from '@/components/meeting/save-recording-dialog';
import { useChat } from '@/hooks/use-chat';
import { useChatStore } from '@/stores/chat-store';
import { useUiStore } from '@/stores/ui-store';

// 인증 구역 공통 앱 셸(ADR-0020 포털). claude.ai식 고정 사이드바 — 모든 화면에서 유지되고
// 본문(children)만 교체. 세션 목록 로드·사이드바 콜백은 여기서 전역 스토어(use-chat)로 연결한다.
export function AppShell({ children }: { children: React.ReactNode }) {
  const { loadSessions, selectSession, newChat, rename, remove } = useChat();
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = React.useState(false);
  // 데스크톱 사이드바 접힘 상태(claude.ai식). 공유 스토어 — AppHeader의 펼치기 버튼과 함께 쓴다.
  const collapsed = useUiStore((s) => s.sidebarCollapsed);
  const setCollapsed = useUiStore((s) => s.setSidebarCollapsed);

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
        {/* 전 화면 공통 헤더 — 제목·액션은 각 화면이 usePageHeader로 주입(header-store 슬롯). */}
        <AppHeader onOpenMenu={() => setMobileOpen(true)} />
        {children}
      </div>

      {/* 모바일 사이드바 Sheet — 트리거는 AppHeader 햄버거, 본체는 여기서 1개 유지(사이드바 콜백 소유). */}
      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent side="left" className="w-72 p-0">
          <SheetTitle className="sr-only">메뉴</SheetTitle>
          {sidebar({
            onNavigate: () => setMobileOpen(false),
            onToggleCollapse: () => setMobileOpen(false),
          })}
        </SheetContent>
      </Sheet>

      <SettingsDialog />
      {/* 전역 녹음 바·저장 다이얼로그 — 메뉴 이동 중에도 녹음 유지 (meeting-minutes) */}
      <RecordingBar />
      <SaveRecordingDialog />
    </div>
  );
}
