'use client'

import { useState } from 'react'
import { Mic, Pause, Play, Square, Upload, X, FileAudio } from 'lucide-react'
import { meetingApi } from '@/api/meetings'
import { useRecorderStore } from '@/stores/recorder-store'
import { logger } from '@/lib/logger'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { formatTimestamp } from '../lib'

const LANGUAGES = [
  { value: 'ko-KR', label: '한국어' },
  { value: 'en-US', label: 'English' },
  { value: 'ja-JP', label: '日本語' },
  { value: 'zh-CN', label: '中文' },
]

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreated: () => void
}

export function NewMeetingDialog({ open, onOpenChange, onCreated }: Props) {
  const [title, setTitle] = useState('')
  const [language, setLanguage] = useState('ko-KR')
  const [file, setFile] = useState<File | null>(null)
  const [submitting, setSubmitting] = useState(false)

  // Recording lives in a module-level store so it survives navigation / dialog
  // close. Finalizing a recording is handled by the global SaveRecordingDialog.
  const { status, elapsedMs, error, start, pause, resume, stop } = useRecorderStore()
  const recording = status === 'recording'
  const paused = status === 'paused'

  const close = () => {
    onOpenChange(false)
    setTitle('')
    setLanguage('ko-KR')
    setFile(null)
  }

  const handleUploadSubmit = async () => {
    if (!file) {
      toast.error('오디오 파일을 선택하세요.')
      return
    }
    setSubmitting(true)
    try {
      await meetingApi.create({ file, filename: file.name, title: title.trim(), language })
      toast.success('회의록 생성을 시작했습니다. 처리에는 수 분이 걸릴 수 있습니다.')
      onCreated()
      close()
    } catch (err) {
      logger.error(err)
      toast.error('업로드에 실패했습니다.')
    } finally {
      setSubmitting(false)
    }
  }

  // Stopping closes this dialog; the global SaveRecordingDialog opens to finalize.
  const handleStop = () => {
    stop()
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={(o) => (o ? onOpenChange(true) : close())}>
      <DialogContent className='max-w-lg'>
        <DialogHeader>
          <DialogTitle>새 회의록</DialogTitle>
          <DialogDescription>녹음하거나 오디오 파일을 업로드해 회의록을 생성합니다.</DialogDescription>
        </DialogHeader>

        <Tabs defaultValue='record'>
          <TabsList className='grid w-full grid-cols-2'>
            <TabsTrigger value='record'>
              <Mic className='mr-2 h-4 w-4' /> 녹음하기
            </TabsTrigger>
            <TabsTrigger value='upload'>
              <Upload className='mr-2 h-4 w-4' /> 파일 업로드
            </TabsTrigger>
          </TabsList>

          {/* Record tab — start/control only; finalize is global */}
          <TabsContent value='record' className='space-y-4 pt-2'>
            <div className='flex flex-col items-center gap-4 rounded-lg border bg-muted/20 py-8'>
              <div className='font-mono text-3xl tabular-nums'>{formatTimestamp(elapsedMs)}</div>
              {error && <p className='px-6 text-center text-sm text-red-500'>{error}</p>}
              <div className='flex items-center gap-2'>
                {status === 'idle' && (
                  <Button onClick={start} className='gap-2'>
                    <Mic className='h-4 w-4' /> 녹음 시작
                  </Button>
                )}
                {recording && (
                  <Button variant='secondary' onClick={pause} className='gap-2'>
                    <Pause className='h-4 w-4' /> 일시정지
                  </Button>
                )}
                {paused && (
                  <Button variant='secondary' onClick={resume} className='gap-2'>
                    <Play className='h-4 w-4' /> 재개
                  </Button>
                )}
                {(recording || paused) && (
                  <Button variant='destructive' onClick={handleStop} className='gap-2'>
                    <Square className='h-4 w-4' /> 정지
                  </Button>
                )}
              </div>
              {(recording || paused) && (
                <p className='text-xs text-muted-foreground'>
                  이 창을 닫고 다른 메뉴를 사용해도 녹음은 계속됩니다. 정지하면 저장 창이 열립니다.
                </p>
              )}
            </div>
            <div className='flex justify-end'>
              <Button variant='outline' onClick={() => onOpenChange(false)}>
                닫기
              </Button>
            </div>
          </TabsContent>

          {/* Upload tab */}
          <TabsContent value='upload' className='space-y-4 pt-2'>
            <div className='grid grid-cols-2 gap-3'>
              <div className='space-y-1.5'>
                <Label htmlFor='meeting-title'>제목</Label>
                <Input
                  id='meeting-title'
                  placeholder='예: 주간 기획회의'
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
              </div>
              <div className='space-y-1.5'>
                <Label htmlFor='meeting-lang'>언어</Label>
                <select
                  id='meeting-lang'
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
            {!file ? (
              <label
                htmlFor='audio-upload'
                className='flex h-32 w-full cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed hover:bg-muted/40'
              >
                <Upload className='mb-2 h-8 w-8 text-muted-foreground' />
                <p className='text-sm text-muted-foreground'>
                  <span className='font-semibold'>클릭하여 업로드</span> 또는 드래그 앤 드롭
                </p>
                <p className='text-xs text-muted-foreground'>mp3, m4a, wav, webm, ogg (최대 500MB)</p>
                <input
                  id='audio-upload'
                  type='file'
                  className='hidden'
                  accept='.mp3,.m4a,.wav,.webm,.ogg,.mp4,.flac,.aac,audio/*'
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                />
              </label>
            ) : (
              <div className='flex items-center justify-between rounded-md border bg-muted p-3 text-sm'>
                <div className='flex min-w-0 items-center gap-2'>
                  <FileAudio className='h-4 w-4 shrink-0 text-primary' />
                  <span className='truncate'>{file.name}</span>
                  <span className='shrink-0 text-xs text-muted-foreground'>
                    {(file.size / (1024 * 1024)).toFixed(1)}MB
                  </span>
                </div>
                <Button variant='ghost' size='sm' className='h-6 w-6 p-0' onClick={() => setFile(null)}>
                  <X className='h-3 w-3' />
                </Button>
              </div>
            )}
            <div className='flex justify-end gap-2'>
              <Button variant='outline' onClick={close}>
                닫기
              </Button>
              <Button onClick={handleUploadSubmit} disabled={!file || submitting}>
                {submitting ? '생성 중…' : '생성'}
              </Button>
            </div>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}
