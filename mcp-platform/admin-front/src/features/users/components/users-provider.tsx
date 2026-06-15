'use client'

import React, { useState, useEffect } from 'react'
import useDialogState from '@/hooks/use-dialog-state'
import { type User } from '../data/schema'
import * as userApi from '@/api/users'
import { logger } from '@/lib/logger'

type UsersDialogType = 'invite' | 'add' | 'edit' | 'delete'

type UsersContextType = {
  open: UsersDialogType | null
  setOpen: (str: UsersDialogType | null) => void
  currentRow: User | null
  setCurrentRow: React.Dispatch<React.SetStateAction<User | null>>
  users: User[]
  addUser: (user: Partial<User>) => Promise<void>
  updateUser: (user: User) => Promise<void>
  deleteUser: (user: User) => Promise<void>
  isLoading: boolean
}

const UsersContext = React.createContext<UsersContextType | null>(null)

export function UsersProvider({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useDialogState<UsersDialogType>(null)
  const [currentRow, setCurrentRow] = useState<User | null>(null)
  const [users, setUsers] = useState<User[]>([])
  const [isLoading, setIsLoading] = useState(false)

  const fetchUsers = async () => {
    setIsLoading(true)
    try {
      const data = await userApi.getUsers()
      setUsers(data)
    } catch (error) {
      logger.error('Failed to fetch users', error)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchUsers()
  }, [])

  const addUser = async (user: Partial<User>) => {
    try {
      const newUser = await userApi.createUser(user)
      setUsers((prev) => [newUser, ...prev])
    } catch (error) {
      logger.error('Failed to create user', error)
      throw error
    }
  }

  const updateUser = async (updatedUser: User) => {
    try {
      const res = await userApi.updateUser(updatedUser.id, updatedUser)
      setUsers((prev) =>
        prev.map((user) => (user.id === res.id ? res : user))
      )
    } catch (error) {
       logger.error('Failed to update user', error)
       throw error
    }
  }

  const deleteUser = async (deletedUser: User) => {
    try {
      await userApi.deleteUser(deletedUser.id)
      setUsers((prev) => prev.filter((user) => user.id !== deletedUser.id))
    } catch (error) {
      logger.error('Failed to delete user', error)
      throw error
    }
  }

  return (
    <UsersContext.Provider
      value={{
        open,
        setOpen,
        currentRow,
        setCurrentRow,
        users,
        addUser,
        updateUser,
        deleteUser,
        isLoading,
      }}
    >
      {children}
    </UsersContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export const useUsers = () => {
  const usersContext = React.useContext(UsersContext)

  if (!usersContext) {
    throw new Error('useUsers has to be used within <UsersContext>')
  }

  return usersContext
}
