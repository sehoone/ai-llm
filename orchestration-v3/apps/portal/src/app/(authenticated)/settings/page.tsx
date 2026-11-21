'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { useSettingsStore } from '@/stores/settings-store';

// 설정은 claude.ai식 레이어 팝업(SettingsDialog, AppShell에서 렌더)으로 전환됨.
// 전체 페이지 라우트는 보존하되 — 직접 URL·북마크 진입 시 팝업을 열고 챗으로 되돌린다.
export default function SettingsPage() {
  const router = useRouter();
  const setOpen = useSettingsStore((s) => s.setOpen);

  React.useEffect(() => {
    setOpen(true);
    router.replace('/chat');
  }, [router, setOpen]);

  return null;
}
