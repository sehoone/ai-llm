'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Plus, Bot, Edit, Trash2, MessageCircle, Globe, GlobeLock } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Header } from '@/components/layout/header'
import { Main } from '@/components/layout/main'
import { Search } from '@/components/search'
import { ThemeSwitch } from '@/components/theme-switch'
import { ConfigDrawer } from '@/components/config-drawer'
import { ProfileDropdown } from '@/components/profile-dropdown'
import { agentApi, type Agent } from '@/api/agents'
import { toast } from 'sonner'
import { logger } from '@/lib/logger'

export function Agents() {
  const [agents, setAgents] = useState<Agent[]>([])
  const router = useRouter()

  useEffect(() => {
    agentApi.getAll().then(setAgents).catch((e) => {
      logger.error('Failed to load agents', e)
      toast.error('에이전트 목록을 불러오지 못했습니다')
    })
  }, [])

  const handleDelete = async (id: string) => {
    if (!confirm('이 에이전트를 삭제하시겠습니까?')) return
    try {
      await agentApi.delete(id)
      setAgents((prev) => prev.filter((a) => a.id !== id))
      toast.success('에이전트가 삭제되었습니다')
    } catch (e) {
      logger.error('Failed to delete agent', e)
      toast.error('삭제에 실패했습니다')
    }
  }

  const handleTogglePublish = async (id: string) => {
    try {
      const updated = await agentApi.togglePublish(id)
      setAgents((prev) => prev.map((a) => (a.id === id ? updated : a)))
      toast.success(updated.is_published ? '게시되었습니다' : '게시가 취소되었습니다')
    } catch (e) {
      logger.error('Failed to toggle publish', e)
      toast.error('상태 변경에 실패했습니다')
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
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold tracking-tight">Agents</h2>
            <p className="text-muted-foreground">RAG 리소스와 프롬프트를 설정한 챗봇 에이전트를 관리합니다.</p>
          </div>
          <Button onClick={() => router.push('/agents/new')}>
            <Plus className="mr-2 h-4 w-4" /> 에이전트 생성
          </Button>
        </div>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {agents.map((agent) => (
            <Card key={agent.id} className="flex flex-col">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="p-2 bg-primary/10 rounded-full">
                      <Bot className="h-6 w-6 text-primary" />
                    </div>
                    <CardTitle className="text-xl">{agent.name}</CardTitle>
                  </div>
                  <Badge variant={agent.is_published ? 'default' : 'secondary'}>
                    {agent.is_published ? '게시됨' : '비공개'}
                  </Badge>
                </div>
                <CardDescription>{agent.description || '설명 없음'}</CardDescription>
              </CardHeader>
              <CardContent className="flex-1 space-y-2">
                <div className="flex flex-wrap gap-1">
                  <Badge variant="outline" className="text-xs">{agent.model}</Badge>
                  {agent.rag_enabled && (
                    <Badge variant="outline" className="text-xs">
                      RAG {agent.rag_keys.length}개
                    </Badge>
                  )}
                  {agent.tools_enabled.map((t) => (
                    <Badge key={t} variant="outline" className="text-xs">{t}</Badge>
                  ))}
                </div>
                {agent.system_prompt && (
                  <p className="text-sm text-muted-foreground line-clamp-2">{agent.system_prompt}</p>
                )}
              </CardContent>
              <CardFooter className="flex justify-end gap-1 flex-wrap">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleTogglePublish(agent.id)}
                  title={agent.is_published ? '게시 취소' : '게시'}
                >
                  {agent.is_published ? <GlobeLock className="h-4 w-4" /> : <Globe className="h-4 w-4" />}
                </Button>
                <Button variant="ghost" size="sm" onClick={() => router.push(`/agents/${agent.id}`)}>
                  <Edit className="h-4 w-4 mr-1" /> 편집
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-destructive hover:text-destructive"
                  onClick={() => handleDelete(agent.id)}
                >
                  <Trash2 className="h-4 w-4 mr-1" /> 삭제
                </Button>
                <Button size="sm" onClick={() => router.push(`/agents/${agent.id}/chat`)}>
                  <MessageCircle className="h-4 w-4 mr-1" /> 채팅
                </Button>
              </CardFooter>
            </Card>
          ))}
          {agents.length === 0 && (
            <div className="col-span-full text-center py-16 text-muted-foreground">
              에이전트가 없습니다. 새 에이전트를 만들어보세요.
            </div>
          )}
        </div>
      </Main>
    </>
  )
}
