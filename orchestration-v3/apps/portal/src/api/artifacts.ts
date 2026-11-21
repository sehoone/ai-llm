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
  created_at: string;
  updated_at: string;
}

export interface ArtifactDetail extends ArtifactSummary {
  content: string;
}

export interface ArtifactVersionItem {
  version: number;
  content: string;
  created_at: string;
}

export interface PublicArtifact {
  title: string;
  artifact_type: string;
  content: string;
  version: number;
}

export const artifactApi = {
  // 사용자가 직접 만드는 standalone 아티팩트(세션 없음). 백엔드가 v1로 저장.
  create: async (body: {
    title: string;
    artifact_type: string;
    content: string;
  }): Promise<ArtifactDetail> => (await api.post<ArtifactDetail>(BASE, body)).data,
  listBySession: async (sessionId: number): Promise<ArtifactSummary[]> =>
    (await api.get<{ items: ArtifactSummary[] }>(BASE, { params: { session_id: sessionId } })).data
      .items,
  // session_id 없이 호출 → 내 전체 아티팩트(최신순). 백엔드 list_user_artifacts.
  listAll: async (): Promise<ArtifactSummary[]> =>
    (await api.get<{ items: ArtifactSummary[] }>(BASE)).data.items,
  get: async (id: string): Promise<ArtifactDetail> =>
    (await api.get<ArtifactDetail>(`${BASE}/${id}`)).data,
  // 버전 히스토리(최신순).
  getVersions: async (id: string): Promise<ArtifactVersionItem[]> =>
    (await api.get<{ items: ArtifactVersionItem[] }>(`${BASE}/${id}/versions`)).data.items,
  getVersion: async (id: string, version: number): Promise<ArtifactVersionItem> =>
    (await api.get<ArtifactVersionItem>(`${BASE}/${id}/versions/${version}`)).data,
  remove: async (id: string): Promise<void> => {
    await api.delete(`${BASE}/${id}`);
  },
  publish: async (id: string): Promise<string> =>
    (await api.post<{ public_token: string }>(`${BASE}/${id}/publish`)).data.public_token,
  // 인터랙티브 아티팩트 데이터(소유자). 샌드박스가 host 브리지로 호출.
  getData: async (id: string): Promise<Record<string, unknown>> =>
    (await api.get<{ data: Record<string, unknown> }>(`${BASE}/${id}/data`)).data.data,
  setData: async (id: string, data: Record<string, unknown>): Promise<void> => {
    await api.put(`${BASE}/${id}/data`, { data });
  },
  getPublic: async (token: string): Promise<PublicArtifact> =>
    (await api.get<PublicArtifact>(`v1/public/artifacts/${token}`)).data,
};
