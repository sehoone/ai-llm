import api from './axios';

// artifact 도메인 (ADR-0013). 스트리밍 산출물 + 버전 + 공개 링크.
const BASE = 'v1/artifacts';

export interface ArtifactSummary {
  id: string;
  session_id: string;
  identifier: string;
  artifact_type: string;
  title: string;
  current_version: number;
  is_published: boolean;
  public_token: string | null;
}

export interface ArtifactDetail extends ArtifactSummary {
  content: string;
}

export interface PublicArtifact {
  title: string;
  artifact_type: string;
  content: string;
  version: number;
}

export const artifactApi = {
  listBySession: async (sessionId: number): Promise<ArtifactSummary[]> =>
    (await api.get<{ items: ArtifactSummary[] }>(BASE, { params: { session_id: sessionId } })).data
      .items,
  get: async (id: string): Promise<ArtifactDetail> =>
    (await api.get<ArtifactDetail>(`${BASE}/${id}`)).data,
  publish: async (id: string): Promise<string> =>
    (await api.post<{ public_token: string }>(`${BASE}/${id}/publish`)).data.public_token,
  getPublic: async (token: string): Promise<PublicArtifact> =>
    (await api.get<PublicArtifact>(`v1/public/artifacts/${token}`)).data,
};
