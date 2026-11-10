import api from './axios'
import type { User } from '@/features/users/data/schema'

// 백엔드 V3는 snake_case(ApiResponse 계약), web 레이어는 camelCase.
// axios 인터셉터는 래퍼만 벗기고 key 변환은 하지 않으므로 여기서 매핑한다.
// (web src/api 재매핑 — CLAUDE.md "ADR-0006 후속")
interface UserApi {
  id: number | string
  username: string
  email: string
  role: string
  status: User['status']
  created_at?: string | null
}

const toCamel = (u: UserApi): User => ({
  id: u.id,
  username: u.username,
  email: u.email,
  role: u.role,
  status: u.status,
  createdAt: u.created_at ? new Date(u.created_at) : undefined,
})

export const getUsers = async (): Promise<User[]> => {
  const response = await api.get('v1/users')
  const list: UserApi[] = response.data?.content ?? response.data
  return list.map(toCamel)
}

export const createUser = async (data: Partial<User> & { password?: string }): Promise<User> => {
  const response = await api.post<UserApi>('v1/users', data)
  return toCamel(response.data)
}

export const updateUser = async (id: string | number, data: Partial<User> & { password?: string }): Promise<User> => {
  const { password, ...rest } = data
  const payload = password ? { ...rest, password } : rest
  const response = await api.patch<UserApi>(`v1/users/${id}`, payload)
  return toCamel(response.data)
}

export const deleteUser = async (id: string | number): Promise<void> => {
  await api.delete(`v1/users/${id}`)
}
