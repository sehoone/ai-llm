'use client'

import { useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Loader2, Pencil, RefreshCw, Share2, Users } from 'lucide-react'
import { meetingApi, type MeetingStatus, type MinutesContent } from '@/api/meetings'
import { logger } from '@/lib/logger'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { StatusBadge } from './components/status-badge'
import { TranscriptTimeline } from './components/transcript-timeline'
import { AudioPlayer } from './components/audio-player'
import { MinutesPanel } from './components/minutes-panel'
import { MinutesEditor } from './components/minutes-editor'
import { SpeakerMappingDialog } from './components/speaker-mapping-dialog'
import { formatDuration, isProcessing, STATUS_LABEL } from './lib'

const PROGRESS_STEPS: { key: MeetingStatus; label: string }[] = [
  { key: 'UPLOADED', label: '오디오 업로드' },
  { key: 'TRANSCRIBING', label: '음성 전사 (화자분리)' },
  { key: 'SUMMARIZING', label: 'AI 요약' },
]

const STEP_ORDER: MeetingStatus[] = [
  'UPLOADED',
  'TRANSCRIBING',
  'TRANSCRIBED',
  'SUMMARIZING',
  'COMPLETED',
]

function ProcessingView({ status }: { status: MeetingStatus }) {
  const currentIdx = STEP_ORDER.indexOf(status)
  return (
    <div className='mx-auto mt-16 max-w-md rounded-lg border p-8'>
      <div className='mb-6 flex items-center gap-3'>
        <Loader2 className='h-6 w-6 animate-spin text-primary' />
        <h3 className='text-lg font-semibold'>회의록을 생성하고 있어요…</h3>
      </div>
      <ol className='space-y-3'>
        {PROGRESS_STEPS.map((step) => {
          const stepIdx = STEP_ORDER.indexOf(step.key)
          const done = currentIdx > stepIdx
          const active =
            status === step.key ||
            (step.key === 'TRANSCRIBING' && status === 'TRANSCRIBED')
          return (
            <li key={step.key} className='flex items-center gap-3 text-sm'>
              <span
                className={`flex h-5 w-5 items-center justify-center rounded-full text-xs ${
                  done
                    ? 'bg-green-500 text-white'
                    : active
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted text-muted-foreground'
                }`}
              >
                {done ? '✓' : active ? '◐' : '○'}
              </span>
              <span className={active ? 'font-medium' : 'text-muted-foreground'}>{step.label}</span>
            </li>
          )
        })}
      </ol>
      <p className='mt-6 text-xs text-muted-foreground'>보통 5~10분 정도 소요됩니다.</p>
    </div>
  )
}

export function MeetingDetail() {
  const router = useRouter()
  const params = useParams()
  const id = params.id as string
  const [speakerOpen, setSpeakerOpen] = useState(false)
  const [regenerating, setRegenerating] = useState(false)
  const [editing, setEditing] = useState(false)
  const [savingMinutes, setSavingMinutes] = useState(false)

  const {
    data: meeting,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ['meeting', id],
    queryFn: () => meetingApi.get(id),
    refetchInterval: (query) => (query.state.data && isProcessing(query.state.data.status) ? 3000 : false),
  })

  const completed = meeting?.status === 'COMPLETED'
  const transcribed = meeting ? !isProcessing(meeting.status) || meeting.status === 'TRANSCRIBED' : false

  const { data: transcript, refetch: refetchTranscript } = useQuery({
    queryKey: ['meeting-transcript', id],
    queryFn: () => meetingApi.getTranscript(id),
    enabled: !!meeting && (completed || transcribed),
  })

  const handleRegenerate = async () => {
    setRegenerating(true)
    try {
      await meetingApi.regenerate(id)
      toast.success('회의록을 재생성했습니다.')
      refetch()
    } catch (error) {
      logger.error(error)
      toast.error('재생성에 실패했습니다.')
    } finally {
      setRegenerating(false)
    }
  }

  const handleSaveMinutes = async (content: MinutesContent, summary: string) => {
    setSavingMinutes(true)
    try {
      await meetingApi.updateMinutes(id, content, summary)
      toast.success('회의록을 저장했습니다.')
      setEditing(false)
      refetch()
    } catch (error) {
      logger.error(error)
      toast.error('저장에 실패했습니다.')
    } finally {
      setSavingMinutes(false)
    }
  }

  const handlePublish = async () => {
    try {
      const { public_token } = await meetingApi.publish(id)
      const url = `${window.location.origin}/artifact/${public_token}`
      await navigator.clipboard.writeText(url)
      toast.success('공개 링크를 클립보드에 복사했습니다.')
      refetch()
    } catch (error) {
      logger.error(error)
      toast.error('발행에 실패했습니다.')
    }
  }

  if (isLoading || !meeting) {
    return (
      <div className='space-y-4 p-4 md:p-8'>
        <Skeleton className='h-8 w-64' />
        <Skeleton className='h-96 w-full' />
      </div>
    )
  }

  return (
    <div className='flex flex-col gap-4 p-4 md:p-8'>
      <div className='flex flex-wrap items-center justify-between gap-3'>
        <div className='flex items-center gap-3'>
          <Button variant='ghost' size='sm' onClick={() => router.push('/meeting-minutes')}>
            <ArrowLeft className='h-4 w-4' />
          </Button>
          <h2 className='text-2xl font-bold tracking-tight'>
            {meeting.title || meeting.audio_filename || '회의록'}
          </h2>
          <StatusBadge status={meeting.status} />
          <span className='text-sm text-muted-foreground'>{formatDuration(meeting.audio_duration_sec)}</span>
        </div>
        {completed && (
          <div className='flex items-center gap-2'>
            <Button variant='outline' size='sm' onClick={() => setSpeakerOpen(true)}>
              <Users className='mr-2 h-4 w-4' /> 화자 지정
            </Button>
            <Button variant='outline' size='sm' onClick={handleRegenerate} disabled={regenerating}>
              <RefreshCw className={`mr-2 h-4 w-4 ${regenerating ? 'animate-spin' : ''}`} /> 재생성
            </Button>
            <Button size='sm' onClick={handlePublish}>
              <Share2 className='mr-2 h-4 w-4' /> 공유
            </Button>
          </div>
        )}
      </div>

      <AudioPlayer meetingId={id} filename={meeting.audio_filename} />

      {meeting.status === 'FAILED' ? (
        <div className='mx-auto mt-16 max-w-md rounded-lg border border-red-200 bg-red-50 p-6 text-center dark:border-red-900/50 dark:bg-red-950/30'>
          <p className='font-medium text-red-700 dark:text-red-300'>{STATUS_LABEL.FAILED}</p>
          <p className='mt-2 text-sm text-red-600 dark:text-red-400'>
            {meeting.error_message || '처리 중 오류가 발생했습니다.'}
          </p>
        </div>
      ) : meeting.status === 'SAVED' ? (
        <div className='mx-auto mt-16 max-w-md rounded-lg border border-emerald-200 bg-emerald-50 p-6 text-center dark:border-emerald-900/50 dark:bg-emerald-950/30'>
          <p className='text-lg font-medium text-emerald-700 dark:text-emerald-300'>
            ✅ 오디오가 저장되었습니다
          </p>
          <p className='mt-2 text-sm text-emerald-600 dark:text-emerald-400'>
            파일 업로드·저장은 정상 완료되었습니다. 전사(STT)를 사용할 수 없어 회의록은 생성되지 않았습니다.
          </p>
          <p className='mt-1 text-xs text-muted-foreground'>
            {meeting.audio_filename}
            {meeting.audio_duration_sec ? ` · ${formatDuration(meeting.audio_duration_sec)}` : ''}
          </p>
        </div>
      ) : !completed ? (
        <ProcessingView status={meeting.status} />
      ) : (
        <div className='grid grid-cols-1 gap-4 lg:grid-cols-2'>
          <div className='rounded-lg border'>
            <div className='border-b px-4 py-2 text-sm font-semibold'>📝 전사 (화자별)</div>
            <TranscriptTimeline segments={transcript?.segments ?? []} />
          </div>
          <div className='rounded-lg border'>
            <div className='flex items-center justify-between border-b px-4 py-2 text-sm font-semibold'>
              <span>📋 회의록</span>
              {meeting.minutes && !editing && (
                <Button variant='ghost' size='sm' className='h-7' onClick={() => setEditing(true)}>
                  <Pencil className='mr-1.5 h-3.5 w-3.5' /> 편집
                </Button>
              )}
            </div>
            {meeting.minutes ? (
              editing ? (
                <MinutesEditor
                  content={meeting.minutes.content}
                  saving={savingMinutes}
                  onCancel={() => setEditing(false)}
                  onSave={handleSaveMinutes}
                />
              ) : (
                <MinutesPanel content={meeting.minutes.content} />
              )
            ) : (
              <p className='p-4 text-sm text-muted-foreground'>회의록이 아직 없습니다.</p>
            )}
          </div>
        </div>
      )}

      {transcript && (
        <SpeakerMappingDialog
          meetingId={id}
          segments={transcript.segments}
          open={speakerOpen}
          onOpenChange={setSpeakerOpen}
          onSaved={() => {
            refetchTranscript()
            refetch()
          }}
        />
      )}
    </div>
  )
}
