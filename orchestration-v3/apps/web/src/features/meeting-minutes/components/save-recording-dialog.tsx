'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useQueryClient } from '@tanstack/react-query'
import { meetingApi } from '@/api/meetings'
import { useRecorderStore } from '@/stores/recorder-store'
import { logger } from '@/lib/logger'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { formatTimestamp } from '../lib'

const LANGUAGES = [
  { value: 'ko-KR', label: '한국어' },
  { value: 'en-US', label: 'English' },
  { value: 'ja-JP', label: '日本語' },
  { value: 'zh-CN', label: '中文' },
]

/**
 * Global finalize dialog for a finished recording. Mounted once in the
 * authenticated layout so a recording can be saved from any page, and so a
 * recovered recording (after reload/crash) can be saved too.
 */
export function SaveRecordingDialog() {
  const router = useRouter()
  const queryClient = useQueryClient()
  const { status, blob, blobUrl, saveOpen, recovered, elapsedMs, setSaveOpen, discard } =
    useRecorderStore()
  const [title, setTitle] = useState('')
  const [language, setLanguage] = useState('ko-KR')
  const [submitting, setSubmitting] = useState(false)

  const open = saveOpen && status === 'stopped' && !!blob

  const handleSave = async () => {
    if (!blob) return
    setSubmitting(true)
    try {
      await meetingApi.create({
        file: blob,
        filename: `recording-${Date.now()}.webm`,
        title: title.trim(),
        language,
      })
      toast.success('회의록 생성을 시작했습니다. 처리에는 수 분이 걸릴 수 있습니다.')
      queryClient.invalidateQueries({ queryKey: ['meetings'] })
      setTitle('')
      discard() // clears blob + IndexedDB + closes (saveOpen=false)
      router.push('/meeting-minutes')
    } catch (err) {
      logger.error(err)
      toast.error('업로드에 실패했습니다.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDiscard = () => {
    if (!confirm('이 녹음을 삭제하시겠습니까?')) return
    setTitle('')
    discard()
  }

  return (
    <Dialog open={open} onOpenChange={(o) => setSaveOpen(o)}>
      <DialogContent className='max-w-md'>
        <DialogHeader>
          <DialogTitle>녹음 저장</DialogTitle>
          <DialogDescription>
            {recovered
              ? '이전 세션에서 복구된 녹음입니다. 제목을 입력하고 저장하세요.'
              : '녹음이 완료되었습니다. 제목을 입력하고 저장하세요.'}
          </DialogDescription>
        </DialogHeader>

        <div className='space-y-4'>
          {blobUrl && (
            <div className='flex items-center gap-2 rounded-md border bg-muted/20 p-2'>
              <span className='shrink-0 text-xs text-muted-foreground'>🎧 {formatTimestamp(elapsedMs)}</span>
              <audio controls src={blobUrl} className='min-w-0 flex-1'>
                <track kind='captions' />
              </audio>
            </div>
          )}

          <div className='grid grid-cols-2 gap-3'>
            <div className='space-y-1.5'>
              <Label htmlFor='save-title'>제목</Label>
              <Input
                id='save-title'
                placeholder='예: 주간 기획회의'
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </div>
            <div className='space-y-1.5'>
              <Label htmlFor='save-lang'>언어</Label>
              <select
                id='save-lang'
                className='flex h-9 w-full items-center rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring'
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
              >
                {LANGUAGES.map((l) => (
                  <option key={l.value} value={l.value}>
                    {l.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        <DialogFooter className='gap-2 sm:justify-between'>
          <Button variant='ghost' onClick={handleDiscard} disabled={submitting}>
            삭제
          </Button>
          <div className='flex gap-2'>
            <Button variant='outline' onClick={() => setSaveOpen(false)} disabled={submitting}>
              나중에
            </Button>
            <Button onClick={handleSave} disabled={submitting}>
              {submitting ? '저장 중…' : '저장'}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
