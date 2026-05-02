import api from './axios'
import type { LLMResource } from '@/features/llm-resources/data/schema'

export interface ChatModel {
  id: number
  name: string
  model_name: string | null
}

export const getChatModels = async (): Promise<ChatModel[]> => {
  const response = await api.get('v1/llm-resources/chat-models')
  return response.data
}

export const getLLMResources = async (): Promise<LLMResource[]> => {
  const response = await api.get('v1/llm-resources')
  return response.data
}

export const createLLMResource = async (data: Partial<LLMResource>): Promise<LLMResource> => {
  const response = await api.post('v1/llm-resources', data)
  return response.data
}

export const updateLLMResource = async (id: number, data: Partial<LLMResource>): Promise<LLMResource> => {
  const response = await api.put(`v1/llm-resources/${id}`, data)
  return response.data
}

export const deleteLLMResource = async (id: number): Promise<void> => {
  await api.delete(`v1/llm-resources/${id}`)
}
