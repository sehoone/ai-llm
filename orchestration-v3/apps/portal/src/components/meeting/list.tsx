'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { Mic, Plus, Trash2 } from 'lucide-react'
import { meetingApi } from '@/api/meetings'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { usePageHeader } from '@/hooks/use-page-header'
import { StatusBadge } from './status-badge'
import { NewMeetingDialog } from './new-meeting-dialog'
import { formatDuration, isProcessing } from './lib'
import { logger } from '@/lib/logger'

export function MeetingList() {
  const router = useRouter()
  const [dialogOpen, setDialogOpen] = useState(false)

  const { data: meetings = [], isLoading, refetch } = useQuery({
    queryKey: ['meetings'],
    queryFn: meetingApi.list,
    refetchInterval: (query) => {
      const items = query.state.data
      return items && items.some((m) => isProcessing(m.status)) ? 3000 : false
    },
  })

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    if (!confirm('이 회의록을 삭제하시겠습니까?')) return
    try {
      await meetingApi.remove(id)
      toast.success('삭제되었습니다.')
      refetch()
    } catch (error) {
      logger.error(error)
      toast.error('삭제에 실패했습니다.')
    }
  }

  usePageHeader(
    {
      title: (
        <span className='flex items-center gap-2'>
          <Mic className='size-4' /> 회의록
        </span>
      ),
      actions: (
        <Button size='sm' onClick={() => setDialogOpen(true)}>
          <Plus className='size-4' /> 새 회의록
        </Button>
      ),
    },
    []
  )

  return (
    <div className='mx-auto flex w-full max-w-4xl flex-col gap-4 p-4 md:p-8'>
      <p className='text-sm text-muted-foreground'>녹음 또는 파일로 회의록을 자동 생성합니다.</p>

      <div className='overflow-hidden rounded-lg border'>
        {/* header row */}
        <div className='flex items-center gap-3 border-b bg-muted/40 px-4 py-2 text-xs font-medium text-muted-foreground'>
          <span className='flex-1'>제목</span>
          <span className='w-28 shrink-0'>상태</span>
          <span className='w-16 shrink-0'>길이</span>
          <span className='hidden w-40 shrink-0 sm:block'>생성일</span>
          <span className='w-8 shrink-0' />
        </div>

        {isLoading ? (
          Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className='border-b px-4 py-3 last:border-b-0'>
              <Skeleton className='h-6 w-full' />
            </div>
          ))
        ) : meetings.length === 0 ? (
          <div className='px-4 py-10 text-center text-sm text-muted-foreground'>
            아직 회의록이 없습니다. “새 회의록”으로 시작하세요.
          </div>
        ) : (
          meetings.map((m) => (
            <div
              key={m.id}
              className='flex cursor-pointer items-center gap-3 border-b px-4 py-3 text-sm last:border-b-0 hover:bg-muted/40'
              onClick={() => router.push(`/meeting-minutes/${m.id}`)}
            >
              <span className='min-w-0 flex-1 truncate font-medium'>
                {m.title || m.audio_filename || '제목 없음'}
              </span>
              <span className='w-28 shrink-0'>
                <StatusBadge status={m.status} />
              </span>
              <span className='w-16 shrink-0'>{formatDuration(m.audio_duration_sec)}</span>
              <span className='hidden w-40 shrink-0 text-muted-foreground sm:block'>
                {new Date(m.created_at).toLocaleString('ko-KR')}
              </span>
              <span className='w-8 shrink-0'>
                <Button
                  variant='ghost'
                  size='sm'
                  className='h-7 w-7 p-0'
                  onClick={(e) => handleDelete(e, m.id)}
                >
                  <Trash2 className='h-4 w-4 text-muted-foreground' />
                </Button>
              </span>
            </div>
          ))
        )}
      </div>

      <NewMeetingDialog open={dialogOpen} onOpenChange={setDialogOpen} onCreated={refetch} />
    </div>
  )
}
