import api from '@/api/axios'

export interface StatsResponse {
  totalUsers: number
  activeUsers: number
  totalApiKeys: number
  activeApiKeys: number
}

export const getStats = async (): Promise<StatsResponse> => {
  const response = await api.get<StatsResponse>('v1/stats')
  return response.data
}
