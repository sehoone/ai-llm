import api from './axios';

// connector 도메인 (ADR-0022). 사내 MCP 서버 등록. 도구 로드/위험도는 engine/agent.
// NOTE: 라이브 대화 tool-calling 그래프 wiring은 후속(ADR-0022 후속) — 현재는 등록·미리보기까지.
const BASE = 'v1/connectors';

export interface Connector {
  id: string;
  user_id: number;
  name: string;
  description: string | null;
  mcp_url: string;
  has_credential: boolean;
  enabled: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface ConnectorTool {
  name: string;
  description: string;
  risk: string;
}

export const connectorsApi = {
  list: async (): Promise<Connector[]> => (await api.get<Connector[]>(BASE)).data,
  get: async (id: string): Promise<Connector> => (await api.get<Connector>(`${BASE}/${id}`)).data,
  create: async (body: {
    name: string;
    description?: string;
    mcp_url: string;
    credential_ref?: string;
    enabled?: boolean;
  }): Promise<Connector> => (await api.post<Connector>(BASE, body)).data,
  update: async (
    id: string,
    body: Partial<{
      name: string;
      description: string;
      mcp_url: string;
      credential_ref: string;
      enabled: boolean;
    }>
  ): Promise<Connector> => (await api.put<Connector>(`${BASE}/${id}`, body)).data,
  remove: async (id: string): Promise<void> => {
    await api.delete(`${BASE}/${id}`);
  },
  previewTools: async (id: string): Promise<ConnectorTool[]> =>
    (await api.get<ConnectorTool[]>(`${BASE}/${id}/tools`)).data,
};
