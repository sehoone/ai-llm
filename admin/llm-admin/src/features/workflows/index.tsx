'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Plus, Zap, Edit, Trash2, Play, Globe } from 'lucide-react'
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
import { ProfileDropdown } from '@/components/profile-dropdown'
import { ConfigDrawer } from '@/components/config-drawer'
import { workflowApi, type WorkflowListItem } from '@/api/workflows'
import { toast } from 'sonner'
import { logger } from '@/lib/logger'
import { formatDistanceToNow } from 'date-fns'
import { ko } from 'date-fns/locale'

export function Workflows() {
  const [workflows, setWorkflows] = useState<WorkflowListItem[]>([])
  const [loading, setLoading] = useState(true)
  const router = useRouter()

  useEffect(() => {
    workflowApi.list().then((data) => {
      setWorkflows(data)
    }).catch((err) => {
      logger.error('Failed to load workflows', err)
      toast.error('워크플로우 목록을 불러오지 못했습니다')
    }).finally(() => setLoading(false))
  }, [])

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`"${name}" 워크플로우를 삭제하시겠습니까?`)) return
    try {
      await workflowApi.delete(id)
      setWorkflows((prev) => prev.filter((w) => w.id !== id))
      toast.success('삭제됨')
    } catch (err) {
      logger.error('Delete failed', err)
      toast.error('삭제 실패')
    }
  }

  return (
    <>
      <Header fixed>
        <Search />
        <div className='ms-auto flex items-center space-x-4'>
          <ThemeSwitch />
          <ConfigDrawer />
          <ProfileDropdown />
        </div>
      </Header>

      <Main>
        <div className='flex items-center justify-between mb-6'>
          <div>
            <h2 className='text-2xl font-bold tracking-tight'>Workflows</h2>
            <p className='text-muted-foreground'>노드 기반 AI 워크플로우를 생성하고 실행합니다.</p>
          </div>
          <Button onClick={() => router.push('/workflows/new')}>
            <Plus className='mr-2 h-4 w-4' /> 새 워크플로우
          </Button>
        </div>

        {loading && (
          <div className='text-center py-16 text-muted-foreground text-sm'>불러오는 중...</div>
        )}

        {!loading && workflows.length === 0 && (
          <div className='text-center py-16 border border-dashed rounded-xl'>
            <Zap className='h-10 w-10 mx-auto text-muted-foreground mb-3' />
            <p className='text-muted-foreground text-sm'>워크플로우가 없습니다.</p>
            <Button className='mt-4' onClick={() => router.push('/workflows/new')}>
              <Plus className='mr-2 h-4 w-4' /> 첫 워크플로우 만들기
            </Button>
          </div>
        )}

        <div className='grid gap-4 md:grid-cols-2 lg:grid-cols-3'>
          {workflows.map((wf) => (
            <Card key={wf.id} className='flex flex-col hover:shadow-md transition-shadow'>
              <CardHeader>
                <div className='flex items-start gap-2'>
                  <div className='p-2 bg-primary/10 rounded-full shrink-0'>
                    <Zap className='h-5 w-5 text-primary' />
                  </div>
                  <div className='min-w-0'>
                    <CardTitle className='text-base truncate'>{wf.name}</CardTitle>
                    <CardDescription className='text-xs mt-0.5'>
                      {formatDistanceToNow(new Date(wf.updated_at), { addSuffix: true, locale: ko })} 수정됨
                    </CardDescription>
                  </div>
                  {wf.is_published && (
                    <Badge variant='secondary' className='ml-auto text-[10px] shrink-0'>
                      <Globe className='h-2.5 w-2.5 mr-1' />
                      Published
                    </Badge>
                  )}
                </div>
              </CardHeader>
              {wf.description && (
                <CardContent className='flex-1 pt-0'>
                  <p className='text-xs text-muted-foreground line-clamp-2'>{wf.description}</p>
                </CardContent>
              )}
              <CardFooter className='flex justify-end gap-1.5 pt-2'>
                <Button
                  variant='ghost'
                  size='sm'
                  className='text-destructive hover:text-destructive h-7 text-xs'
                  onClick={() => handleDelete(wf.id, wf.name)}
                >
                  <Trash2 className='h-3.5 w-3.5 mr-1' /> 삭제
                </Button>
                <Button
                  variant='outline'
                  size='sm'
                  className='h-7 text-xs'
                  onClick={() => router.push(`/workflows/${wf.id}/edit`)}
                >
                  <Edit className='h-3.5 w-3.5 mr-1' /> 편집
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>
      </Main>
    </>
  )
}
