'use client';

import { Menu, PanelLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useHeaderStore } from '@/stores/header-store';
import { useUiStore } from '@/stores/ui-store';

// 인증 구역 전 화면 공통 상단 바(ADR-0020). 뼈대는 여기서 고정 렌더하고, 제목·우측 액션은
// 각 화면이 usePageHeader로 주입한 header-store 슬롯을 읽어 표시한다. 좌측 네비 토글은
// 모바일(햄버거)·데스크톱 접힘(펼치기)을 한 바에서 모두 처리 — 기존 모바일 헤더·플로팅 버튼·
// chat 전용 헤더를 하나로 통합.
export function AppHeader({ onOpenMenu }: { onOpenMenu: () => void }) {
  const title = useHeaderStore((s) => s.title);
  const actions = useHeaderStore((s) => s.actions);
  const collapsed = useUiStore((s) => s.sidebarCollapsed);
  const setCollapsed = useUiStore((s) => s.setSidebarCollapsed);

  return (
    <header className="flex h-14 shrink-0 items-center gap-2 border-b border-border bg-background/80 px-3 backdrop-blur">
      {/* 모바일: 사이드바 Sheet 열기 */}
      <Button
        variant="ghost"
        size="icon"
        className="size-8 shrink-0 md:hidden"
        onClick={onOpenMenu}
        aria-label="메뉴 열기"
      >
        <Menu className="size-4" />
      </Button>

      {/* 데스크톱: 사이드바 접힘 시 펼치기 */}
      {collapsed && (
        <Button
          variant="ghost"
          size="icon"
          className="hidden size-8 shrink-0 text-muted-foreground md:flex"
          onClick={() => setCollapsed(false)}
          aria-label="사이드바 펼치기"
        >
          <PanelLeft className="size-4" />
        </Button>
      )}

      <div className="flex min-w-0 flex-1 items-center gap-2 text-sm font-medium">
        {title ?? 'AI 포털'}
      </div>

      <div className="flex shrink-0 items-center gap-1">{actions}</div>
    </header>
  );
}
