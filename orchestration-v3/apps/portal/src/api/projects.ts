import api from './axios';

// project 도메인 (ADR-0021). 대화·지침·지식을 묶는 작업공간. 대화는 chat 스택 재사용.
const BASE = 'v1/projects';

export interface Project {
  id: string;
  user_id: number;
  name: string;
  description: string | null;
  instructions: string;
  rag_key: string;
  rag_group: string;
  icon: string;
  color: string;
  created_at: string;
  updated_at: string | null;
}

export interface ProjectSession {
  id: number;
  title: string;
}

export interface ProjectKnowledge {
  id: number;
  filename: string;
}

export interface ProjectArtifact {
  id: string;
  identifier: string;
  title: string;
  artifact_type: string;
  current_version: number;
  session_id: number;
}

export const projectsApi = {
  list: async (): Promise<Project[]> => (await api.get<Project[]>(`${BASE}/`)).data,
  get: async (id: string): Promise<Project> => (await api.get<Project>(`${BASE}/${id}`)).data,
  create: async (body: {
    name: string;
    description?: string;
    instructions?: string;
    icon?: string;
    color?: string;
  }): Promise<Project> => (await api.post<Project>(`${BASE}/`, body)).data,
  update: async (
    id: string,
    body: Partial<Pick<Project, 'name' | 'description' | 'instructions' | 'icon' | 'color'>>
  ): Promise<Project> => (await api.put<Project>(`${BASE}/${id}`, body)).data,
  remove: async (id: string): Promise<void> => {
    await api.delete(`${BASE}/${id}`);
  },

  // 소속 대화
  listSessions: async (id: string): Promise<ProjectSession[]> =>
    (await api.get<ProjectSession[]>(`${BASE}/${id}/sessions`)).data,
  createSession: async (id: string, title?: string): Promise<ProjectSession> =>
    (await api.post<ProjectSession>(`${BASE}/${id}/sessions`, { title })).data,

  // 지식 (rag 재사용)
  listKnowledge: async (id: string): Promise<ProjectKnowledge[]> =>
    (await api.get<ProjectKnowledge[]>(`${BASE}/${id}/knowledge`)).data,
  addKnowledge: async (id: string, filename: string, content: string): Promise<ProjectKnowledge> =>
    (await api.post<ProjectKnowledge>(`${BASE}/${id}/knowledge`, { filename, content })).data,
  deleteKnowledge: async (id: string, docId: number): Promise<void> => {
    await api.delete(`${BASE}/${id}/knowledge/${docId}`);
  },

  // 기본 활성 스킬 (ADR-0024 §4) — 이 프로젝트 대화에 자동 적용될 스킬 id. 순서=합성 우선순위.
  listSkills: async (id: string): Promise<string[]> =>
    (await api.get<string[]>(`${BASE}/${id}/skills`)).data,
  setSkills: async (id: string, skillIds: string[]): Promise<string[]> =>
    (await api.put<string[]>(`${BASE}/${id}/skills`, { skill_ids: skillIds })).data,

  // 산출물 집계
  listArtifacts: async (id: string): Promise<ProjectArtifact[]> =>
    (await api.get<ProjectArtifact[]>(`${BASE}/${id}/artifacts`)).data,
};
