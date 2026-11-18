import api from './axios';

// 사용자용 chat 모델 목록(ADR-0010) — GET /llm-resources/chat-models (인증 사용자).
export interface ChatModel {
  id: number;
  name: string;
  model_name: string | null;
}

export const llmResourceApi = {
  chatModels: async (): Promise<ChatModel[]> =>
    (await api.get<ChatModel[]>('v1/llm-resources/chat-models')).data,
};
