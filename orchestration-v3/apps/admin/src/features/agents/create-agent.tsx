'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Header } from '@/components/layout/header'
import { Main } from '@/components/layout/main'
import { Search } from '@/components/search'
import { ThemeSwitch } from '@/components/theme-switch'
import { ConfigDrawer } from '@/components/config-drawer'
import { ProfileDropdown } from '@/components/profile-dropdown'
import { agentApi, type CreateAgentData } from '@/api/agents'
import { AgentForm } from './components/agent-form'
import { toast } from 'sonner'
import { logger } from '@/lib/logger'

export function CreateAgent() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (data: CreateAgentData) => {
    setIsLoading(true)
    try {
      await agentApi.create(data)
      toast.success('에이전트가 생성되었습니다')
      router.push('/agents')
    } catch (e) {
      logger.error('Failed to create agent', e)
      toast.error('에이전트 생성에 실패했습니다')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <>
      <Header fixed>
        <Search />
        <div className="ms-auto flex items-center space-x-4">
          <ThemeSwitch />
          <ConfigDrawer />
          <ProfileDropdown />
        </div>
      </Header>

      <Main>
        <div className="mb-6">
          <h2 className="text-2xl font-bold tracking-tight">에이전트 생성</h2>
          <p className="text-muted-foreground">새 챗봇 에이전트를 설정합니다.</p>
        </div>
        <div className="max-w-2xl">
          <AgentForm onSubmit={handleSubmit} isLoading={isLoading} />
        </div>
      </Main>
    </>
  )
}
