import { create } from 'zustand'

import type { ArtifactState } from '@/types/chat-api'

interface ArtifactStore {
  /** All artifacts seen in the current session, keyed by identifier. */
  artifacts: Record<string, ArtifactState>
  /** Identifier of the artifact shown in the canvas, or null when closed. */
  activeId: string | null
  isOpen: boolean

  /** Begin (or restart) streaming an artifact — opens the canvas on it. */
  startArtifact: (meta: { identifier: string; type: string; title: string }) => void
  /** Append streamed content to an artifact's current draft. */
  appendDelta: (identifier: string, text: string) => void
  /** Mark an artifact's stream as finished, recording its persisted version. */
  endArtifact: (identifier: string, version?: number) => void
  /** Insert or replace a fully-known artifact (e.g. loaded from history). */
  upsertArtifact: (artifact: ArtifactState) => void

  open: (identifier: string) => void
  close: () => void
  setActive: (identifier: string) => void
  /** Drop all artifacts (e.g. when switching sessions). */
  reset: () => void
}

export const useArtifactStore = create<ArtifactStore>((set) => ({
  artifacts: {},
  activeId: null,
  isOpen: false,

  startArtifact: ({ identifier, type, title }) =>
    set((state) => {
      const prev = state.artifacts[identifier]
      return {
        artifacts: {
          ...state.artifacts,
          [identifier]: {
            identifier,
            type,
            title,
            content: '',
            // Bump optimistic version when re-streaming an existing artifact.
            version: prev ? prev.version + 1 : 1,
            isStreaming: true,
            serverId: prev?.serverId,
          },
        },
        activeId: identifier,
        isOpen: true,
      }
    }),

  appendDelta: (identifier, text) =>
    set((state) => {
      const cur = state.artifacts[identifier]
      if (!cur) return state
      return {
        artifacts: {
          ...state.artifacts,
          [identifier]: { ...cur, content: cur.content + text },
        },
      }
    }),

  endArtifact: (identifier, version) =>
    set((state) => {
      const cur = state.artifacts[identifier]
      if (!cur) return state
      return {
        artifacts: {
          ...state.artifacts,
          [identifier]: {
            ...cur,
            isStreaming: false,
            version: version ?? cur.version,
          },
        },
      }
    }),

  upsertArtifact: (artifact) =>
    set((state) => ({
      artifacts: { ...state.artifacts, [artifact.identifier]: artifact },
    })),

  open: (identifier) => set({ activeId: identifier, isOpen: true }),
  close: () => set({ isOpen: false }),
  setActive: (identifier) => set({ activeId: identifier }),
  reset: () => set({ artifacts: {}, activeId: null, isOpen: false }),
}))
