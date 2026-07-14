import api from './axios'

export interface DocumentItem {
  id: number
  title: string
  content: string
  model: string
  createdAt: string
}

export interface PagedResponse<T> {
  content: T[]
  page: number
  size: number
  totalElements: number
  totalPages: number
}

export interface CreateEmbeddingRequest {
  title: string
  content: string
}

export interface SearchRequest {
  query: string
  topK: number
  threshold: number
}

export interface SearchResult {
  id: number
  title: string
  content: string
  score: number
  createdAt: string
}

export const createEmbedding = async (data: CreateEmbeddingRequest): Promise<DocumentItem> => {
  const res = await api.post<DocumentItem>('v1/embeddings', data)
  return res.data
}

export const listEmbeddings = async (page = 0, size = 10): Promise<PagedResponse<DocumentItem>> => {
  const res = await api.get<PagedResponse<DocumentItem>>('v1/embeddings', { params: { page, size } })
  return res.data
}

export const deleteEmbedding = async (id: number): Promise<void> => {
  await api.delete(`v1/embeddings/${id}`)
}

export const deleteAllEmbeddings = async (): Promise<void> => {
  await api.delete('v1/embeddings')
}

export const searchEmbeddings = async (data: SearchRequest): Promise<SearchResult[]> => {
  const res = await api.post<SearchResult[]>('v1/search', data)
  return res.data
}

// ── 일괄 업로드 ─────────────────────────────────────────────

export interface BulkEmbeddingItem {
  id: string | number
  title: string
  desc: string
}

export interface BulkEmbeddingResultItem {
  id: string | number
  title: string
  success: boolean
  documentId?: number
  error?: string
}

export interface BulkEmbeddingResponse {
  total: number
  successCount: number
  failedCount: number
  results: BulkEmbeddingResultItem[]
}

export const bulkUploadEmbeddings = async (
  items: BulkEmbeddingItem[]
): Promise<BulkEmbeddingResponse> => {
  const res = await api.post<BulkEmbeddingResponse>('v1/embeddings/batch', items)
  return res.data
}
