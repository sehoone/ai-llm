import api from './axios'
import type { User } from '@/features/users/data/schema'

export const getUsers = async (): Promise<User[]> => {
  const response = await api.get('v1/users')
  return response.data?.content ?? response.data
}

export const createUser = async (data: Partial<User> & { password?: string }): Promise<User> => {
  const response = await api.post('v1/users', data)
  return response.data
}

export const updateUser = async (id: string | number, data: Partial<User> & { password?: string }): Promise<User> => {
  const response = await api.patch(`v1/users/${id}`, data)
  return response.data
}

export const deleteUser = async (id: string | number): Promise<void> => {
  await api.delete(`v1/users/${id}`)
}
