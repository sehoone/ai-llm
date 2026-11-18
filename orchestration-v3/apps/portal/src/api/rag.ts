import api from './axios';

// RAG 지식베이스 그룹(ADR-0012) — 챗에 rag_group(이름)으로 컨텍스트 사전 주입.
export interface RagGroup {
  id: string;
  name: string;
  description: string | null;
  doc_count: number;
}

export const ragApi = {
  listGroups: async (): Promise<RagGroup[]> =>
    (await api.get<RagGroup[]>('v1/rag/groups')).data,
};
