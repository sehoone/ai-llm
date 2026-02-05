/* eslint-disable @typescript-eslint/no-explicit-any */
import { logger } from '@/lib/logger'
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
  uploadDocument: async (params: DocumentUploadParams) => {
    const formData = new FormData()
    formData.append('file', params.file)
    formData.append('rag_key', params.rag_key)
    formData.append('rag_group', params.rag_group)
    formData.append('rag_type', params.rag_type)
    if (params.tags) formData.append('tags', params.tags)

    const response = await api.post<DocumentResponse>(
        '/api/v1/rag/upload',
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
      
      const response = await api.get<DocumentResponse[]>(`/api/v1/rag/documents?${params.toString()}`)
      return response.data
  },

  getDocument: async (id: number) => {
    const response = await api.get<DocumentDetailResponse>(`/api/v1/rag/documents/${id}`)
    return response.data
  },

  deleteDocument: async (id: number) => {
    await api.delete(`/api/v1/rag/documents/${id}`)
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
      '/api/v1/rag/natural-language-search',
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

    let buffer = '';
    let seenBytes = 0;

    try {
        await api.post('/api/v1/rag/natural-language-search', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
            responseType: 'text', // Important to get text instead of trying to parse JSON
            onDownloadProgress: (progressEvent) => {
                const xhr = progressEvent.event.target
                const response = xhr.response
                const newData = response.slice(seenBytes)
                seenBytes = response.length;
                
                buffer += newData;
                const lines = buffer.split('\n');
                buffer = lines.pop() || ''; // Keep the last partial line in buffer

                for (const line of lines) {
                    if (!line.trim()) continue;
                    try {
                        const json = JSON.parse(line);
                        onData(json);
                    } catch (e) {
                         logger.error('Error parsing JSON line from stream', e);
                    }
                }
            }
        });
    } catch (error) {
        onError(error);
        throw error;
    }
  },
}
