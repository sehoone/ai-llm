import api from '@/api/axios'

export interface ApiKey {
  id: number
  name: string
  key: string
  isActive: boolean
  expiresAt?: string | null
  createdAt: string
}

export interface CreateApiKeyRequest {
  name: string
  expiresAt?: string | null
}

// 백엔드 V3는 snake_case(ApiResponse 계약), web 레이어는 camelCase.
// axios 인터셉터는 래퍼만 벗기고 key 변환은 하지 않으므로 여기서 매핑한다.
// (web src/api 재매핑 — CLAUDE.md "ADR-0006 후속")
interface ApiKeyApi {
  id: number
  name: string
  key: string
  is_active: boolean
  expires_at: string | null
  created_at: string
}

const toCamel = (k: ApiKeyApi): ApiKey => ({
  id: k.id,
  name: k.name,
  key: k.key,
  isActive: k.is_active,
  expiresAt: k.expires_at,
  createdAt: k.created_at,
})

export const getApiKeys = async (): Promise<ApiKey[]> => {
  const response = await api.get<ApiKeyApi[]>('v1/api-keys')
  return response.data.map(toCamel)
}

export const createApiKey = async (data: CreateApiKeyRequest): Promise<ApiKey> => {
  const response = await api.post<ApiKeyApi>('v1/api-keys', {
    name: data.name,
    expires_at: data.expiresAt ?? null,
  })
  return toCamel(response.data)
}

export const revokeApiKey = async (id: number): Promise<void> => {
  await api.delete(`v1/api-keys/${id}`)
}
