'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { Header } from '@/components/layout/header'
import { Main } from '@/components/layout/main'
import { Search } from '@/components/search'
import { ThemeSwitch } from '@/components/theme-switch'
import { ConfigDrawer } from '@/components/config-drawer'
import { ProfileDropdown } from '@/components/profile-dropdown'
import { Button } from '@/components/ui/button'
import { ArrowLeft, MessageCircle } from 'lucide-react'
import { agentApi, type Agent, type UpdateAgentData } from '@/api/agents'
import { AgentForm } from './components/agent-form'
import { toast } from 'sonner'
import { logger } from '@/lib/logger'

export function EditAgent() {
  const params = useParams()
  const router = useRouter()
  const agentId = params.agentId as string
  const [agent, setAgent] = useState<Agent | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    agentApi.get(agentId).then(setAgent).catch((e) => {
      logger.error('Failed to load agent', e)
      toast.error('에이전트를 불러오지 못했습니다')
      router.push('/agents')
    })
  }, [agentId, router])

  const handleSubmit = async (data: UpdateAgentData) => {
    setIsLoading(true)
    try {
      await agentApi.update(agentId, data)
      toast.success('저장되었습니다')
      router.push('/agents')
    } catch (e) {
      logger.error('Failed to update agent', e)
      toast.error('저장에 실패했습니다')
    } finally {
      setIsLoading(false)
    }
  }

  if (!agent) {
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
          <div className="text-muted-foreground">불러오는 중...</div>
        </Main>
      </>
    )
  }

  return (
    <>
      <Header fixed>
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => router.push('/agents')}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <h1 className="text-xl font-bold">{agent.name}</h1>
        </div>
        <div className="ms-auto flex items-center space-x-4">
          <Button variant="outline" onClick={() => router.push(`/agents/${agentId}/chat`)}>
            <MessageCircle className="mr-2 h-4 w-4" /> 채팅 테스트
          </Button>
          <ThemeSwitch />
          <ConfigDrawer />
          <ProfileDropdown />
        </div>
      </Header>

      <Main>
        <div className="mb-6">
          <h2 className="text-2xl font-bold tracking-tight">에이전트 편집</h2>
          <p className="text-muted-foreground">에이전트 설정을 수정합니다.</p>
        </div>
        <div className="max-w-2xl">
          <AgentForm initial={agent} onSubmit={handleSubmit} isLoading={isLoading} />
        </div>
      </Main>
    </>
  )
}
