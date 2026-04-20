import api from './axios'

export interface RagGroup {
  id: string
  user_id: number
  name: string
  description?: string
  color: string
  key_count: number
  doc_count: number
  created_at: string
}

export interface RagKey {
  id: string
  user_id: number
  rag_key: string
  rag_group: string
  description?: string
  rag_type: string
  doc_count: number
  created_at: string
}

export interface CreateGroupData {
  name: string
  description?: string
  color?: string
}

export interface UpdateGroupData {
  name?: string
  description?: string
  color?: string
}

export interface CreateKeyData {
  rag_key: string
  rag_group: string
  description?: string
  rag_type?: string
}

export interface UpdateKeyData {
  rag_group?: string
  description?: string
  rag_type?: string
}

const BASE = 'v1/rag'

export const ragGroupApi = {
  // Groups
  listGroups: async (): Promise<RagGroup[]> => {
    const res = await api.get<RagGroup[]>(`${BASE}/groups`)
    return res.data
  },

  createGroup: async (data: CreateGroupData): Promise<RagGroup> => {
    const res = await api.post<RagGroup>(`${BASE}/groups`, data)
    return res.data
  },

  updateGroup: async (id: string, data: UpdateGroupData): Promise<RagGroup> => {
    const res = await api.put<RagGroup>(`${BASE}/groups/${id}`, data)
    return res.data
  },

  deleteGroup: async (id: string): Promise<void> => {
    await api.delete(`${BASE}/groups/${id}`)
  },

  listGroupKeys: async (groupId: string): Promise<RagKey[]> => {
    const res = await api.get<RagKey[]>(`${BASE}/groups/${groupId}/keys`)
    return res.data
  },

  // Keys
  listKeys: async (ragGroup?: string): Promise<RagKey[]> => {
    const params = ragGroup ? `?rag_group=${encodeURIComponent(ragGroup)}` : ''
    const res = await api.get<RagKey[]>(`${BASE}/keys${params}`)
    return res.data
  },

  createKey: async (data: CreateKeyData): Promise<RagKey> => {
    const res = await api.post<RagKey>(`${BASE}/keys`, data)
    return res.data
  },

  updateKey: async (id: string, data: UpdateKeyData): Promise<RagKey> => {
    const res = await api.put<RagKey>(`${BASE}/keys/${id}`, data)
    return res.data
  },

  deleteKey: async (id: string, deleteDocs = false): Promise<void> => {
    await api.delete(`${BASE}/keys/${id}?delete_docs=${deleteDocs}`)
  },
}
