import api from './axios'

export interface DocumentItem {
  id: number
  title: string
  content: string                                           // full_content
  sourceType: string
  status: 'pending' | 'processing' | 'indexed' | 'failed'
  model?: string | null
  errorMessage?: string | null
  createdAt: string
  updatedAt: string
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

export interface ChunkMatch {
  id: number
  chunkIndex: number
  chunkTotal: number
  content: string
  score: number
}

export interface SearchResult {
  documentId: number
  title: string
  fullContent: string
  score: number        // 매칭 청크 중 최고 유사도
  createdAt: string
  matchingChunks: ChunkMatch[]
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

export const retryEmbedding = async (id: number): Promise<DocumentItem> => {
  const res = await api.post<DocumentItem>(`v1/embeddings/${id}/retry`)
  return res.data
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
