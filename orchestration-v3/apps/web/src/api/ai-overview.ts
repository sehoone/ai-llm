import { createNDJSONProgressHandler } from '@/lib/sse-stream'
import api from './axios'

export interface AiOverviewDocumentSummary {
  id: number
  title: string
  source_url: string | null
  status: 'pending' | 'processing' | 'ready' | 'error'
  keyword_count: number
  created_at: string
  updated_at: string
}

export interface AiOverviewKeyword {
  id: number
  keyword: string
  keyword_type: 'keyword' | 'synonym'
  created_at: string
}

export interface AiOverviewDocumentDetail extends AiOverviewDocumentSummary {
  content: string
  keywords: AiOverviewKeyword[]
}

export interface AiOverviewDocumentListResponse {
  total: number
  items: AiOverviewDocumentSummary[]
}

export interface UploadResult {
  job_id: string
  total: number
  skipped: number
}

export interface UploadProgress {
  job_id: string
  total: number
  processed: number
  failed: number
  status: 'running' | 'done'
  recent: { id: number; title: string; keyword_count: number }[]
}

export interface AiOverviewSearchStreamEvent {
  type: 'keywords' | 'sources' | 'chunk' | 'error'
  data: unknown
}

export interface AiOverviewSource {
  id: number
  title: string
  source_url: string | null
  score: number
}

export const aiOverviewApi = {
  listDocuments: async (
    offset = 0,
    limit = 20,
    search = ''
  ): Promise<AiOverviewDocumentListResponse> => {
    const params = new URLSearchParams({ offset: String(offset), limit: String(limit) })
    if (search) params.append('search', search)
    const res = await api.get<AiOverviewDocumentListResponse>(
      `v1/ai-overview/documents?${params}`
    )
    return res.data
  },

  createDocument: async (body: { title: string; content: string; source_url?: string }) => {
    const res = await api.post<{ id: number; title: string; status: string; created_at: string }>(
      'v1/ai-overview/documents',
      body
    )
    return res.data
  },

  getDocument: async (id: number): Promise<AiOverviewDocumentDetail> => {
    const res = await api.get<AiOverviewDocumentDetail>(`v1/ai-overview/documents/${id}`)
    return res.data
  },

  deleteDocument: async (id: number): Promise<void> => {
    await api.delete(`v1/ai-overview/documents/${id}`)
  },

  generateKeywords: async (id: number, systemPrompt?: string, model?: string): Promise<{ doc_id: number; keyword_count: number }> => {
    const body: Record<string, string> = {}
    if (systemPrompt) body.system_prompt = systemPrompt
    if (model) body.model = model
    const res = await api.post<{ doc_id: number; keyword_count: number }>(
      `v1/ai-overview/documents/${id}/generate-keywords`,
      body
    )
    return res.data
  },

  listKeywords: async (id: number): Promise<AiOverviewKeyword[]> => {
    const res = await api.get<AiOverviewKeyword[]>(`v1/ai-overview/documents/${id}/keywords`)
    return res.data
  },

  deleteKeyword: async (docId: number, keywordId: number): Promise<void> => {
    await api.delete(`v1/ai-overview/documents/${docId}/keywords/${keywordId}`)
  },

  deleteAllDocuments: async (): Promise<{ deleted: number }> => {
    const res = await api.delete<{ deleted: number }>('v1/ai-overview/documents/all')
    return res.data
  },

  batchDeleteDocuments: async (ids: number[]): Promise<{ deleted: number }> => {
    const res = await api.delete<{ deleted: number }>('v1/ai-overview/documents/batch', {
      data: { ids },
    })
    return res.data
  },

  uploadDocumentsJson: async (file: File, systemPrompt?: string, model?: string): Promise<UploadResult> => {
    const formData = new FormData()
    formData.append('file', file)
    if (systemPrompt) formData.append('system_prompt', systemPrompt)
    if (model) formData.append('model', model)
    const res = await api.post<UploadResult>('v1/ai-overview/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return res.data
  },

  getUploadProgress: async (jobId: string): Promise<UploadProgress> => {
    const res = await api.get<UploadProgress>(`v1/ai-overview/documents/upload/${jobId}/progress`)
    return res.data
  },

  searchStream: async (
    query: string,
    model: string,
    onData: (event: AiOverviewSearchStreamEvent) => void,
    onError: (error: unknown) => void,
    system_prompt?: string
  ): Promise<void> => {
    const handler = createNDJSONProgressHandler<AiOverviewSearchStreamEvent>((data) => onData(data))
    try {
      await api.post(
        'v1/ai-overview/search',
        { query, model, system_prompt: system_prompt ?? '' },
        { responseType: 'text', onDownloadProgress: handler.onDownloadProgress }
      )
    } catch (error) {
      onError(error)
      throw error
    }
  },
}
