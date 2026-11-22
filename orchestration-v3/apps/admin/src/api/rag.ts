import api from './axios'

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

  // getDocuments: async (rag_key?: string, rag_type?: string) => {
  //   const params = new URLSearchParams()
  //   if (rag_key) params.append('rag_key', rag_key)
  //   if (rag_type) params.append('rag_type', rag_type)
    
  //   const response = await api.get<DocumentResponse[]>(`/rag/documents?${params.toString()}`)
  //   return response.data
  // },
}
