import { create } from 'zustand';

// 앱 셸 레이아웃 UI 상태. 데스크톱 사이드바 접힘(claude.ai식)은 AppShell(사이드바·플로팅 버튼)과
// 챗 헤더(펼치기 버튼)가 함께 쓰므로 지역 useState가 아닌 공유 스토어로 둔다.
interface UiStore {
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (collapsed: boolean) => void;
}

export const useUiStore = create<UiStore>((set) => ({
  sidebarCollapsed: false,
  setSidebarCollapsed: (sidebarCollapsed) => set({ sidebarCollapsed }),
}));
