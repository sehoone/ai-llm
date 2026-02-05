'use client'

import { useEffect, useState } from 'react'
import { Header } from '@/components/layout/header'
import { Main } from '@/components/layout/main'
import { ProfileDropdown } from '@/components/profile-dropdown'
import { Search } from '@/components/search'
import { ThemeSwitch } from '@/components/theme-switch'
import { chatService } from '@/api/chat'
import { type ChatHistoryResponse } from '@/types/chat-api'
import { columns } from './components/columns'
import { DataTable } from './components/data-table'
import { toast } from 'sonner'
import { logger } from '@/lib/logger'

export function ChatHistory() {
  const [data, setData] = useState<ChatHistoryResponse[]>([])
  const [, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      // Fetch more data if needed, currently implementing client side pagination on a chunk of 100
      const history = await chatService.getAllChatHistory(100, 0)
      setData(history)
    } catch (error) {
      logger.error('Failed to load chat history', error)
      toast.error('Failed to load chat history')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <Header>
        <Search />
        <div className='ms-auto flex items-center space-x-4'>
          <ThemeSwitch />
          <ProfileDropdown />
        </div>
      </Header>

      <Main>
        <div className='mb-2 flex items-center justify-between space-y-2'>
          <div>
            <h2 className='text-2xl font-bold tracking-tight'>Chat History</h2>
            <p className='text-muted-foreground'>
              Monitor all user chat interactions.
            </p>
          </div>
        </div>
        <div className='-mx-4 flex-1 overflow-auto px-4 py-1 lg:flex-row lg:space-x-12 lg:space-y-0'>
          <DataTable columns={columns} data={data} />
        </div>
      </Main>
    </>
  )
}
