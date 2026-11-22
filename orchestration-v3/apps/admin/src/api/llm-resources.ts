import api from './axios'
import type { LLMResource } from '@/features/llm-resources/data/schema'

export interface ChatModel {
  id: number
  name: string
  modelName: string | null
}

// 백엔드 V3는 snake_case(ApiResponse 계약), web 레이어는 camelCase.
// axios 인터셉터는 래퍼만 벗기고 key 변환은 하지 않으므로 여기서 양방향 매핑한다.
// (web src/api 재매핑 — CLAUDE.md "ADR-0006 후속")

interface LLMResourceApi {
  id: number
  name: string
  resource_type: string
  model_name: string | null
  provider: string
  api_base: string
  deployment_name: string | null
  api_version: string | null
  region: string | null
  priority: number
  weight: number
  is_active: boolean
}

interface ChatModelApi {
  id: number
  name: string
  model_name: string | null
}

const toCamel = (r: LLMResourceApi): LLMResource => ({
  id: r.id,
  name: r.name,
  resourceType: (r.resource_type as 'chat' | 'embedding') ?? 'chat',
  // apiKey는 응답에 포함되지 않음(민감 정보). 스키마상 키는 필수라 undefined로 명시.
  apiKey: undefined,
  modelName: r.model_name ?? undefined,
  provider: r.provider,
  apiBase: r.api_base,
  deploymentName: r.deployment_name ?? undefined,
  apiVersion: r.api_version ?? undefined,
  region: r.region ?? undefined,
  priority: r.priority,
  weight: r.weight,
  isActive: r.is_active,
})

// camelCase 폼 데이터 → 백엔드 snake_case 바디. 정의된 키만 전송(PATCH는 부분 업데이트).
const toSnake = (data: Partial<LLMResource>): Record<string, unknown> => {
  const out: Record<string, unknown> = {}
  if (data.name !== undefined) out.name = data.name
  if (data.resourceType !== undefined) out.resource_type = data.resourceType
  if (data.modelName !== undefined) out.model_name = data.modelName
  if (data.provider !== undefined) out.provider = data.provider
  if (data.apiBase !== undefined) out.api_base = data.apiBase
  if (data.apiKey !== undefined) out.api_key = data.apiKey
  if (data.deploymentName !== undefined) out.deployment_name = data.deploymentName
  if (data.apiVersion !== undefined) out.api_version = data.apiVersion
  if (data.region !== undefined) out.region = data.region
  if (data.priority !== undefined) out.priority = data.priority
  if (data.weight !== undefined) out.weight = data.weight
  if (data.isActive !== undefined) out.is_active = data.isActive
  return out
}

export const getChatModels = async (): Promise<ChatModel[]> => {
  const response = await api.get<ChatModelApi[]>('v1/llm-resources/chat-models')
  return response.data.map((m) => ({ id: m.id, name: m.name, modelName: m.model_name }))
}

export const getLLMResources = async (): Promise<LLMResource[]> => {
  const response = await api.get<LLMResourceApi[]>('v1/llm-resources')
  return response.data.map(toCamel)
}

export const createLLMResource = async (data: Partial<LLMResource>): Promise<LLMResource> => {
  const response = await api.post<LLMResourceApi>('v1/llm-resources', toSnake(data))
  return toCamel(response.data)
}

export const updateLLMResource = async (id: number, data: Partial<LLMResource>): Promise<LLMResource> => {
  const response = await api.patch<LLMResourceApi>(`v1/llm-resources/${id}`, toSnake(data))
  return toCamel(response.data)
}

export const deleteLLMResource = async (id: number): Promise<void> => {
  await api.delete(`v1/llm-resources/${id}`)
}
