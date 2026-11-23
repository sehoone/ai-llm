import api from './axios';

// skill 도메인 (ADR-0024). 재사용 지침 프리셋 — 활성 스킬 본문이 chat system prompt에 합성된다.
const BASE = 'v1/skills';

export interface Skill {
  id: string;
  user_id: number;
  name: string;
  description: string | null;
  body: string;
  icon: string;
  color: string;
  created_at: string;
  updated_at: string | null;
}

export const skillsApi = {
  list: async (): Promise<Skill[]> => (await api.get<Skill[]>(BASE)).data,
  get: async (id: string): Promise<Skill> => (await api.get<Skill>(`${BASE}/${id}`)).data,
  create: async (body: {
    name: string;
    description?: string;
    body: string;
    icon?: string;
    color?: string;
  }): Promise<Skill> => (await api.post<Skill>(BASE, body)).data,
  update: async (
    id: string,
    body: Partial<Pick<Skill, 'name' | 'description' | 'body' | 'icon' | 'color'>>
  ): Promise<Skill> => (await api.put<Skill>(`${BASE}/${id}`, body)).data,
  remove: async (id: string): Promise<void> => {
    await api.delete(`${BASE}/${id}`);
  },
  // SKILL.md / .md / .txt / .zip 업로드 → 스킬 1건 생성 (ADR-0024 · claude.ai 참고).
  // Content-Type을 비워 axios가 multipart 경계를 자동 설정하게 한다(기본 json 헤더 덮기).
  importFile: async (file: File): Promise<Skill> => {
    const form = new FormData();
    form.append('file', file);
    return (
      await api.post<Skill>(`${BASE}/import`, form, {
        headers: { 'Content-Type': undefined },
      })
    ).data;
  },
};
