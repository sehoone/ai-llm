'use client'

import { useEffect } from 'react'
import { usePathname } from 'next/navigation'
import { Mic, Pause, Play, Save, Square, Trash2 } from 'lucide-react'
import { useRecorderStore } from '@/stores/recorder-store'
import { Button } from '@/components/ui/button'
import { formatTimestamp } from '../lib'

/**
 * Global floating recording bar. Mounted once in the authenticated layout so the
 * recording keeps running — and stays controllable — while the user navigates
 * between menus. Also warns before unload and recovers an interrupted recording.
 */
export function RecordingBar() {
  const pathname = usePathname()
  const { status, elapsedMs, pause, resume, stop, discard, setSaveOpen, recover } = useRecorderStore()

  // Attempt one-time recovery of an interrupted recording on app load.
  useEffect(() => {
    void recover()
  }, [recover])

  // Warn before leaving/reloading while there is unsaved audio.
  useEffect(() => {
    const unsaved = status === 'recording' || status === 'paused' || status === 'stopped'
    if (!unsaved) return
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault()
      e.returnValue = ''
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [status])

  if (status === 'idle') return null

  const onMeetingPage = pathname?.startsWith('/meeting-minutes')
  const recording = status === 'recording'
  const stopped = status === 'stopped'

  return (
    <div className='fixed bottom-4 left-1/2 z-50 -translate-x-1/2'>
      <div className='flex items-center gap-3 rounded-full border bg-background/95 px-4 py-2 shadow-lg backdrop-blur'>
        {stopped ? (
          <>
            <Mic className='h-4 w-4 text-emerald-500' />
            <span className='text-sm font-medium'>녹음 완료 · {formatTimestamp(elapsedMs)}</span>
            <Button size='sm' className='h-8' onClick={() => setSaveOpen(true)}>
              <Save className='mr-1.5 h-4 w-4' /> 저장하기
            </Button>
            <Button size='sm' variant='ghost' className='h-8 w-8 p-0' onClick={discard} title='삭제'>
              <Trash2 className='h-4 w-4' />
            </Button>
          </>
        ) : (
          <>
            <span className='flex items-center gap-2 text-sm font-medium'>
              <span
                className={`inline-block h-2.5 w-2.5 rounded-full bg-red-500 ${recording ? 'animate-pulse' : 'opacity-50'}`}
              />
              {recording ? 'REC' : '일시정지'} · {formatTimestamp(elapsedMs)}
            </span>
            {recording ? (
              <Button size='sm' variant='secondary' className='h-8' onClick={pause}>
                <Pause className='mr-1.5 h-4 w-4' /> 일시정지
              </Button>
            ) : (
              <Button size='sm' variant='secondary' className='h-8' onClick={resume}>
                <Play className='mr-1.5 h-4 w-4' /> 재개
              </Button>
            )}
            <Button size='sm' variant='destructive' className='h-8' onClick={stop}>
              <Square className='mr-1.5 h-4 w-4' /> 정지
            </Button>
            {!onMeetingPage && <span className='text-xs text-muted-foreground'>다른 메뉴 사용 중에도 녹음됩니다</span>}
          </>
        )}
      </div>
    </div>
  )
}
