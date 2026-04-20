import api from './axios'
import type { User } from '@/features/users/data/schema'

export const getUsers = async (): Promise<User[]> => {
  const response = await api.get('v1/users')

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return response.data.map((u: any) => ({
    ...u,
    createdAt: u.created_at || new Date(),
    updatedAt: u.updated_at || new Date(),
  }))
}

export const createUser = async (data: Partial<User>): Promise<User> => {
  // Backend expects snake_case
  const payload = {
    ...data,
  }
  const response = await api.post('v1/users', payload)
  return {
      ...response.data,
  }
}

export const updateUser = async (id: string | number, data: Partial<User>): Promise<User> => {
   const payload = {
    ...data,
  }
  const response = await api.put(`v1/users/${id}`, payload)
  return {
      ...response.data,
  }
}

export const deleteUser = async (id: string | number): Promise<void> => {
  await api.delete(`v1/users/${id}`)
}
