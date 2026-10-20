/* eslint-disable @typescript-eslint/no-explicit-any */
import { createNDJSONProgressHandler } from '@/lib/sse-stream'
import api from './axios'

export interface RAGSearchResult {
  doc_id: number
  filename: string
  content: string
  similarity: number
}

export interface NaturalLanguageSearchResponse {
  query: string
  summary: string
  results: RAGSearchResult[]
}

export interface NaturalLanguageSearchParams {
  rag_type: 'user_isolated' | 'chatbot_shared' | 'natural_search'
  query: string
  rag_key?: string
  rag_group?: string
  limit?: number
  model?: string
  system_prompt?: string
}

export interface RagGroupResponse {
  id: string
  name: string
  description?: string
  color: string
  key_count: number
  doc_count: number
  created_at: string
}

export interface DocumentUploadParams {
    file: File
    rag_key: string
    rag_group: string
    rag_type: 'user_isolated' | 'chatbot_shared' | 'natural_search'
    tags?: string
}

export interface DocumentResponse {
    id: number
    filename: string
    rag_key: string
    rag_group: string
    rag_type: string
    user_id?: number
    size: number
    created_at: string
}

export interface DocumentDetailResponse extends DocumentResponse {
    content: string
}

export const ragApi = {
  getRagGroups: async (): Promise<RagGroupResponse[]> => {
    const response = await api.get<RagGroupResponse[]>('v1/rag/groups')
    return response.data
  },

  uploadDocument: async (params: DocumentUploadParams) => {
    const formData = new FormData()
    formData.append('file', params.file)
    formData.append('rag_key', params.rag_key)
    formData.append('rag_group', params.rag_group)
    formData.append('rag_type', params.rag_type)
    if (params.tags) formData.append('tags', params.tags)

    const response = await api.post<DocumentResponse>(
        'v1/rag/upload',
        formData,
        {
            headers: {
                'Content-Type': 'multipart/form-data',
            }
        }
    )
    return response.data
  },

  getDocuments: async (rag_key?: string, rag_type?: string) => {
      const params = new URLSearchParams()
      if (rag_key) params.append('rag_key', rag_key)
      if (rag_type) params.append('rag_type', rag_type)
      
      const response = await api.get<DocumentResponse[]>(`v1/rag/documents?${params.toString()}`)
      return response.data
  },

  getDocument: async (id: number) => {
    const response = await api.get<DocumentDetailResponse>(`v1/rag/documents/${id}`)
    return response.data
  },

  deleteDocument: async (id: number) => {
    await api.delete(`v1/rag/documents/${id}`)
  },

  naturalLanguageSearch: async (params: NaturalLanguageSearchParams) => {
    const formData = new FormData()
    formData.append('rag_type', params.rag_type)
    formData.append('query', params.query)
    if (params.rag_key) formData.append('rag_key', params.rag_key)
    if (params.rag_group) formData.append('rag_group', params.rag_group)
    if (params.limit) formData.append('limit', params.limit.toString())
    if (params.model) formData.append('model', params.model)

    const response = await api.post<NaturalLanguageSearchResponse>(
      'v1/rag/natural-language-search',
      formData,
      {
        headers: {
            'Content-Type': 'multipart/form-data',
        }
      }
    )
    return response.data
  },

  naturalLanguageSearchStream: async (
    params: NaturalLanguageSearchParams, 
    onData: (data: any) => void,
    onError: (error: any) => void
  ) => {
    const formData = new FormData()
    formData.append('rag_type', params.rag_type)
    formData.append('query', params.query)
    if (params.rag_key) formData.append('rag_key', params.rag_key)
    if (params.rag_group) formData.append('rag_group', params.rag_group)
    if (params.limit) formData.append('limit', params.limit.toString())
    if (params.model) formData.append('model', params.model)
    if (params.system_prompt) formData.append('system_prompt', params.system_prompt)

    const handler = createNDJSONProgressHandler<any>((data) => onData(data))

    try {
      await api.post('v1/rag/natural-language-search', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        responseType: 'text',
        onDownloadProgress: handler.onDownloadProgress,
      })
    } catch (error) {
      onError(error)
      throw error
    }
  },

  // getDocuments: async (rag_key?: string, rag_type?: string) => {
  //   const params = new URLSearchParams()
  //   if (rag_key) params.append('rag_key', rag_key)
  //   if (rag_type) params.append('rag_type', rag_type)
    
  //   const response = await api.get<DocumentResponse[]>(`/rag/documents?${params.toString()}`)
  //   return response.data
  // },
}
