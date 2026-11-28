'use client';

import * as React from 'react';
import type { ReactNode } from 'react';
import { useHeaderStore } from '@/stores/header-store';

// SSR에선 useLayoutEffect가 경고를 내므로 서버에선 useEffect로 폴백(클라이언트는 페인트 전 세팅 → 깜빡임 방지).
const useIsomorphicLayoutEffect =
  typeof window !== 'undefined' ? React.useLayoutEffect : React.useEffect;

// 화면이 공통 헤더 슬롯에 제목·액션을 주입하는 훅. 라우트 전환 시 이전 제목 잔상을 막기 위해
// 레이아웃 이펙트로 세팅하고 언마운트 시 reset한다. actions에 페이지 핸들러를 클로저로 담을 수
// 있으므로, 최신 상태를 참조하도록 해당 상태/콜백을 deps에 넣는다.
export function usePageHeader(
  spec: { title?: ReactNode; actions?: ReactNode },
  deps: React.DependencyList
) {
  const set = useHeaderStore((s) => s.set);
  const reset = useHeaderStore((s) => s.reset);
  useIsomorphicLayoutEffect(() => {
    set(spec);
    return reset;
  }, deps);
}
