import { create } from 'zustand';

// 설정 레이어 팝업(claude.ai식) 열림 상태. 사이드바 드롭다운이 열고, AppShell이 Dialog를 렌더한다.
interface SettingsStore {
  open: boolean;
  setOpen: (open: boolean) => void;
}

export const useSettingsStore = create<SettingsStore>((set) => ({
  open: false,
  setOpen: (open) => set({ open }),
}));
