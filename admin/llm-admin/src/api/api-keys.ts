import api from '@/api/axios'

export interface ApiKey {
  id: number
  user_id: number
  key: string
  name: string
  expires_at?: string
  is_active: boolean
  created_at: string
}

export interface CreateApiKeyRequest {
  name: string
  expires_at?: string | null
}

export const getApiKeys = async (): Promise<ApiKey[]> => {
  const response = await api.get<ApiKey[]>('/api/v1/api-keys/')
  return response.data
}

export const createApiKey = async (data: CreateApiKeyRequest): Promise<ApiKey> => {
  const response = await api.post<ApiKey>('/api/v1/api-keys/', data)
  return response.data
}

export const revokeApiKey = async (id: number): Promise<ApiKey> => {
  const response = await api.delete<ApiKey>(`/api/v1/api-keys/${id}`)
  return response.data
}
