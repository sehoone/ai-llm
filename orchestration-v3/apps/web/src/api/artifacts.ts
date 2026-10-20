import api from './axios'
import type {
  ArtifactDetail,
  ArtifactSummary,
  ArtifactVersionItem,
} from '@/types/chat-api'

const ARTIFACTS_BASE = 'v1/artifacts'
const PUBLIC_BASE = 'v1/public/artifacts'

export const artifactService = {
  /** List artifacts, optionally scoped to a session (else the whole library). */
  list: async (sessionId?: string): Promise<ArtifactSummary[]> => {
    const response = await api.get<{ items: ArtifactSummary[] }>(ARTIFACTS_BASE, {
      params: sessionId ? { session_id: sessionId } : undefined,
    })
    return response.data.items
  },

  /** Fetch an artifact's current version (metadata + content). */
  get: async (artifactId: string): Promise<ArtifactDetail> => {
    const response = await api.get<ArtifactDetail>(`${ARTIFACTS_BASE}/${artifactId}`)
    return response.data
  },

  /** Fetch the full version history of an artifact (newest first). */
  getVersions: async (artifactId: string): Promise<ArtifactVersionItem[]> => {
    const response = await api.get<{ items: ArtifactVersionItem[] }>(
      `${ARTIFACTS_BASE}/${artifactId}/versions`
    )
    return response.data.items
  },

  /** Fetch a specific version of an artifact. */
  getVersion: async (artifactId: string, version: number): Promise<ArtifactVersionItem> => {
    const response = await api.get<ArtifactVersionItem>(
      `${ARTIFACTS_BASE}/${artifactId}/versions/${version}`
    )
    return response.data
  },

  /** Delete an artifact and all its versions. */
  remove: async (artifactId: string): Promise<void> => {
    await api.delete(`${ARTIFACTS_BASE}/${artifactId}`)
  },

  /** Publish an artifact and return its public share token. */
  publish: async (artifactId: string): Promise<string> => {
    const response = await api.post<{ public_token: string }>(
      `${ARTIFACTS_BASE}/${artifactId}/publish`
    )
    return response.data.public_token
  },

  /** Read an artifact's interactive data (owner). */
  getData: async (artifactId: string): Promise<Record<string, unknown>> => {
    const response = await api.get<{ data: Record<string, unknown> }>(
      `${ARTIFACTS_BASE}/${artifactId}/data`
    )
    return response.data.data
  },

  /** Persist an artifact's interactive data (owner). */
  setData: async (artifactId: string, data: Record<string, unknown>): Promise<void> => {
    await api.put(`${ARTIFACTS_BASE}/${artifactId}/data`, { data })
  },

  /** Public (unauthenticated) relative path for a shared artifact. */
  publicUrl: (token: string): string => `${PUBLIC_BASE}/${token}`,
}
