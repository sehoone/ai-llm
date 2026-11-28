import type { ReactNode } from 'react';
import { create } from 'zustand';

// 공통 앱 헤더(AppHeader)의 슬롯. 각 화면이 usePageHeader로 제목·우측 액션을 주입하면
// AppShell의 단일 헤더가 이를 렌더한다 — chat 동적 제목·페이지별 "새로 만들기"까지 한 곳에서 통일.
interface HeaderStore {
  title: ReactNode | null; // 중앙 제목/맥락 (문자열 또는 커스텀 노드)
  actions: ReactNode | null; // 우측 페이지별 액션
  set: (h: { title?: ReactNode; actions?: ReactNode }) => void;
  reset: () => void;
}

export const useHeaderStore = create<HeaderStore>((set) => ({
  title: null,
  actions: null,
  set: ({ title = null, actions = null }) => set({ title, actions }),
  reset: () => set({ title: null, actions: null }),
}));
