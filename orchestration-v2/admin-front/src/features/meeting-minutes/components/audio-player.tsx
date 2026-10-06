'use client'

import { useEffect, useState } from 'react'
import { Download, Loader2 } from 'lucide-react'
import { meetingApi } from '@/api/meetings'
import { logger } from '@/lib/logger'
import { Button } from '@/components/ui/button'

interface Props {
  meetingId: string
  filename: string
}

/**
 * Fetches the meeting audio as an authenticated blob (the API requires a Bearer
 * token, so a plain <audio src> can't be used), then plays and downloads it via
 * an object URL.
 */
export function AudioPlayer({ meetingId, filename }: Props) {
  const [url, setUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let objectUrl: string | null = null
    let cancelled = false
    meetingApi
      .getAudioBlob(meetingId)
      .then((blob) => {
        if (cancelled) return
        objectUrl = URL.createObjectURL(blob)
        setUrl(objectUrl)
      })
      .catch((e) => {
        logger.error(e)
        if (!cancelled) setError('오디오를 불러오지 못했습니다.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [meetingId])

  return (
    <div className='flex items-center gap-3 rounded-lg border bg-muted/20 p-3'>
      <span className='shrink-0 text-sm font-medium text-muted-foreground'>🎧 녹음 파일</span>
      {loading ? (
        <div className='flex items-center gap-2 text-sm text-muted-foreground'>
          <Loader2 className='h-4 w-4 animate-spin' /> 불러오는 중…
        </div>
      ) : error ? (
        <span className='text-sm text-red-500'>{error}</span>
      ) : (
        url && (
          <>
            {/* No forced height — squishing a native <audio> clips its
                built-in "⋮ more options" overflow menu. */}
            <audio controls src={url} className='min-w-0 flex-1'>
              <track kind='captions' />
            </audio>
            <Button asChild variant='outline' size='sm'>
              <a href={url} download={filename || 'recording'}>
                <Download className='mr-1.5 h-4 w-4' /> 다운로드
              </a>
            </Button>
          </>
        )
      )}
    </div>
  )
}
