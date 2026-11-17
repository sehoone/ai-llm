import { create } from 'zustand';
import type { ArtifactSummary } from '@/api/artifacts';

// 아티팩트 뷰 상태 (ADR-0013). 스트리밍 캡처 + 패널. identifier로 키잉.
export interface ArtifactView {
  identifier: string;
  type: string;
  title: string;
  content: string;
  complete: boolean; // 스트리밍 완료 여부 — iframe 렌더는 완료 후 1회 마운트(재로드 폭주 방지)
  id?: string; // DB id — 영속 후 확정(publish·상세 조회용)
  version?: number;
  isPublished?: boolean;
  publicToken?: string | null;
}

interface ArtifactStore {
  artifacts: Record<string, ArtifactView>;
  panelOpen: boolean;
  activeId: string | null; // identifier

  startArtifact: (identifier: string, type: string, title: string) => void;
  appendArtifact: (identifier: string, delta: string) => void;
  endArtifact: (identifier: string, version?: number) => void;

  openPanel: (identifier: string) => void;
  closePanel: () => void;

  setContent: (identifier: string, content: string) => void;
  mergeSummaries: (items: ArtifactSummary[]) => void;
  setPublished: (identifier: string, token: string) => void;
  reset: () => void;
}

export const useArtifactStore = create<ArtifactStore>((set) => ({
  artifacts: {},
  panelOpen: false,
  activeId: null,

  startArtifact: (identifier, type, title) =>
    set((s) => ({
      artifacts: {
        ...s.artifacts,
        [identifier]: {
          ...(s.artifacts[identifier] ?? {}),
          identifier,
          type: type || 'text/markdown',
          title: title || identifier,
          content: '',
          complete: false,
        },
      },
    })),
  appendArtifact: (identifier, delta) =>
    set((s) => {
      const a = s.artifacts[identifier];
      if (!a) return s;
      return { artifacts: { ...s.artifacts, [identifier]: { ...a, content: a.content + delta } } };
    }),
  endArtifact: (identifier, version) =>
    set((s) => {
      const a = s.artifacts[identifier];
      if (!a) return s;
      return { artifacts: { ...s.artifacts, [identifier]: { ...a, version, complete: true } } };
    }),

  openPanel: (identifier) => set({ panelOpen: true, activeId: identifier }),
  closePanel: () => set({ panelOpen: false }),

  setContent: (identifier, content) =>
    set((s) => {
      const a = s.artifacts[identifier];
      if (!a) return s;
      return { artifacts: { ...s.artifacts, [identifier]: { ...a, content } } };
    }),
  mergeSummaries: (items) =>
    set((s) => {
      const next = { ...s.artifacts };
      for (const it of items) {
        const prev = next[it.identifier];
        next[it.identifier] = {
          identifier: it.identifier,
          type: it.artifact_type,
          title: it.title,
          content: prev?.content ?? '', // content는 지연 로드
          complete: true, // 영속된 아티팩트는 완료 상태
          id: it.id,
          version: it.current_version,
          isPublished: it.is_published,
          publicToken: it.public_token,
        };
      }
      return { artifacts: next };
    }),
  setPublished: (identifier, token) =>
    set((s) => {
      const a = s.artifacts[identifier];
      if (!a) return s;
      return {
        artifacts: {
          ...s.artifacts,
          [identifier]: { ...a, isPublished: true, publicToken: token },
        },
      };
    }),
  reset: () => set({ artifacts: {}, panelOpen: false, activeId: null }),
}));
