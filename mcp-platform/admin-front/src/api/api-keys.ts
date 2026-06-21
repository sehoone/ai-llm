import api from '@/api/axios'
import type { ApiKey } from '@/features/api-keys/data/schema'

export interface CreateApiKeyRequest {
  name: string
  expiresAt?: string | null
}

export const getApiKeys = async (): Promise<ApiKey[]> => {
  const response = await api.get<ApiKey[]>('v1/api-keys')
  return response.data
}

export const createApiKey = async (data: CreateApiKeyRequest): Promise<ApiKey> => {
  const response = await api.post<ApiKey>('v1/api-keys', data)
  return response.data
}

export const revokeApiKey = async (id: number): Promise<void> => {
  await api.delete(`v1/api-keys/${id}`)
}
