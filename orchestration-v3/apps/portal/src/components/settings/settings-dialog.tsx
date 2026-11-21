'use client';

import * as React from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { SettingsPanel } from '@/components/settings/settings-panel';
import { useSettingsStore } from '@/stores/settings-store';

// claude.ai식 설정 레이어 팝업. 전역 스토어로 열림을 제어하고 AppShell이 한 번만 렌더한다.
export function SettingsDialog() {
  const open = useSettingsStore((s) => s.open);
  const setOpen = useSettingsStore((s) => s.setOpen);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="flex h-[80vh] max-h-[640px] w-full max-w-3xl flex-col gap-0 overflow-hidden p-0">
        <DialogHeader className="shrink-0 border-b border-border px-6 py-4">
          <DialogTitle>설정</DialogTitle>
          <DialogDescription className="sr-only">
            프로필·비밀번호·테마·장기 메모리 설정
          </DialogDescription>
        </DialogHeader>
        <SettingsPanel onNavigate={() => setOpen(false)} />
      </DialogContent>
    </Dialog>
  );
}
