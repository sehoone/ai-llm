'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { Mic, Plus, Trash2 } from 'lucide-react'
import { meetingApi } from '@/api/meetings'
import { logger } from '@/lib/logger'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Skeleton } from '@/components/ui/skeleton'
import { StatusBadge } from './components/status-badge'
import { NewMeetingDialog } from './components/new-meeting-dialog'
import { formatDuration, isProcessing } from './lib'

export default function MeetingMinutes() {
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

  return (
    <div className='flex flex-col gap-4 p-4 md:p-8'>
      <div className='flex items-center justify-between'>
        <div>
          <h2 className='flex items-center gap-2 text-3xl font-bold tracking-tight'>
            <Mic className='h-7 w-7' /> Meeting Minutes
          </h2>
          <p className='text-muted-foreground'>녹음 또는 파일로 회의록을 자동 생성합니다.</p>
        </div>
        <Button onClick={() => setDialogOpen(true)}>
          <Plus className='mr-2 h-4 w-4' /> 새 회의록
        </Button>
      </div>

      <div className='rounded-lg border'>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>제목</TableHead>
              <TableHead className='w-[120px]'>상태</TableHead>
              <TableHead className='w-[90px]'>길이</TableHead>
              <TableHead className='w-[160px]'>생성일</TableHead>
              <TableHead className='w-[60px]' />
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 3 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell colSpan={5}>
                    <Skeleton className='h-6 w-full' />
                  </TableCell>
                </TableRow>
              ))
            ) : meetings.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className='py-10 text-center text-muted-foreground'>
                  아직 회의록이 없습니다. “새 회의록”으로 시작하세요.
                </TableCell>
              </TableRow>
            ) : (
              meetings.map((m) => (
                <TableRow
                  key={m.id}
                  className='cursor-pointer'
                  onClick={() => router.push(`/meeting-minutes/${m.id}`)}
                >
                  <TableCell className='font-medium'>
                    {m.title || m.audio_filename || '제목 없음'}
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={m.status} />
                  </TableCell>
                  <TableCell>{formatDuration(m.audio_duration_sec)}</TableCell>
                  <TableCell className='text-muted-foreground'>
                    {new Date(m.created_at).toLocaleString('ko-KR')}
                  </TableCell>
                  <TableCell>
                    <Button
                      variant='ghost'
                      size='sm'
                      className='h-7 w-7 p-0'
                      onClick={(e) => handleDelete(e, m.id)}
                    >
                      <Trash2 className='h-4 w-4 text-muted-foreground' />
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <NewMeetingDialog open={dialogOpen} onOpenChange={setDialogOpen} onCreated={refetch} />
    </div>
  )
}
