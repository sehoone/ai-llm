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
    user_id?: number
    size: number
    created_at: string
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

  naturalLanguageSearch: async (params: NaturalLanguageSearchParams) => {
    const formData = new FormData()
    formData.append('rag_type', params.rag_type)
    formData.append('query', params.query)
    if (params.rag_key) formData.append('rag_key', params.rag_key)
    if (params.rag_group) formData.append('rag_group', params.rag_group)
    if (params.limit) formData.append('limit', params.limit.toString())

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
}
