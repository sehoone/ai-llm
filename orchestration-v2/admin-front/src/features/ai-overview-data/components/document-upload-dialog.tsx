'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'
import { CheckCircle2, FileJson, Upload, XCircle } from 'lucide-react'
import { aiOverviewApi, type UploadProgress } from '@/api/ai-overview'
import { logger } from '@/lib/logger'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

type Step = 'select' | 'progress' | 'done'

interface ParsedPreview {
  valid: { title: string }[]
  skippedCount: number
}

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
}

export function DocumentUploadDialog({ open, onOpenChange, onSuccess }: Props) {
  const [step, setStep] = useState<Step>('select')
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<ParsedPreview | null>(null)
  const [parseError, setParseError] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [uploading, setUploading] = useState(false)

  const [jobId, setJobId] = useState<string | null>(null)
  const [progress, setProgress] = useState<UploadProgress | null>(null)

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }

  useEffect(() => {
    if (step !== 'progress' || !jobId) return

    const poll = async () => {
      try {
        const p = await aiOverviewApi.getUploadProgress(jobId)
        setProgress(p)
        if (p.status === 'done') {
          stopPolling()
          setStep('done')
          onSuccess()
        }
      } catch (e) {
        logger.error('upload progress poll failed', e)
      }
    }

    poll() // immediate first call
    pollRef.current = setInterval(poll, 3000)
    return stopPolling
  }, [step, jobId, onSuccess])

  const reset = () => {
    stopPolling()
    setStep('select')
    setFile(null)
    setPreview(null)
    setParseError(null)
    setJobId(null)
    setProgress(null)
    setUploading(false)
  }

  const parseFile = useCallback((f: File) => {
    setFile(f)
    setParseError(null)
    setPreview(null)

    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const raw = JSON.parse(e.target?.result as string)
        if (!Array.isArray(raw)) {
          setParseError('JSON 파일은 배열 형식이어야 합니다')
          return
        }
        const valid: { title: string }[] = []
        let skippedCount = 0
        for (const item of raw) {
          const title = typeof item?.title === 'string' ? item.title.trim() : ''
          const content = typeof item?.content === 'string' ? item.content.trim() : ''
          if (!title || !content) {
            skippedCount++
          } else {
            valid.push({ title })
          }
        }
        setPreview({ valid, skippedCount })
      } catch {
        setParseError('JSON 파싱에 실패했습니다. 파일 형식을 확인하세요.')
      }
    }
    reader.readAsText(f, 'utf-8')
  }, [])

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (f) parseFile(f)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const f = e.dataTransfer.files?.[0]
    if (f) parseFile(f)
  }

  const handleUpload = async () => {
    if (!file || !preview || preview.valid.length === 0) return
    setUploading(true)
    try {
      const result = await aiOverviewApi.uploadDocumentsJson(file)
      setJobId(result.job_id)
      setProgress({
        job_id: result.job_id,
        total: result.total,
        processed: 0,
        failed: 0,
        status: 'running',
        recent: [],
      })
      setStep('progress')
      toast.success(`${result.total}개 문서 업로드 완료 — 키워드 생성 시작`)
    } catch (e) {
      logger.error('upload failed', e)
      toast.error('업로드에 실패했습니다')
    } finally {
      setUploading(false)
    }
  }

  const pct = progress
    ? Math.round((progress.processed / Math.max(progress.total, 1)) * 100)
    : 0

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) reset(); onOpenChange(v) }}>
      <DialogContent className='max-w-lg'>

        {/* ── Step 1: 파일 선택 ── */}
        {step === 'select' && (
          <>
            <DialogHeader>
              <DialogTitle>문서 업로드</DialogTitle>
              <DialogDescription>
                JSON 배열 파일을 업로드하세요.{' '}
                <code className='text-xs bg-muted px-1 rounded'>
                  [{'{'}title, content, source_url?{'}'}]
                </code>
              </DialogDescription>
            </DialogHeader>

            {/* Drop zone */}
            <div
              className={`mt-2 flex flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed p-8 transition-colors cursor-pointer
                ${isDragging ? 'border-primary bg-primary/5' : 'border-muted-foreground/30 hover:border-primary/50'}`}
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
            >
              <FileJson className='h-10 w-10 text-muted-foreground' />
              {file ? (
                <div className='text-center'>
                  <p className='text-sm font-medium'>{file.name}</p>
                  <p className='text-xs text-muted-foreground'>
                    {(file.size / 1024).toFixed(1)} KB
                  </p>
                </div>
              ) : (
                <div className='text-center'>
                  <p className='text-sm font-medium'>JSON 파일을 드래그하거나 클릭하세요</p>
                  <p className='text-xs text-muted-foreground'>*.json, 배열 형식</p>
                </div>
              )}
              <input
                ref={fileInputRef}
                type='file'
                accept='.json,application/json'
                className='hidden'
                onChange={handleFileChange}
              />
            </div>

            {/* Parse error */}
            {parseError && (
              <p className='text-sm text-destructive flex items-center gap-1.5'>
                <XCircle className='h-4 w-4' /> {parseError}
              </p>
            )}

            {/* Preview */}
            {preview && !parseError && (
              <div className='rounded-md border bg-muted/30 p-3 flex flex-col gap-2'>
                <div className='flex items-center gap-2 text-sm'>
                  <Badge variant='default'>{preview.valid.length}건 업로드 예정</Badge>
                  {preview.skippedCount > 0 && (
                    <Badge variant='secondary'>{preview.skippedCount}건 skip (title/content 없음)</Badge>
                  )}
                </div>
                <div className='max-h-36 overflow-y-auto flex flex-col gap-0.5'>
                  {preview.valid.slice(0, 50).map((v, i) => (
                    <p key={i} className='text-xs text-muted-foreground truncate'>
                      · {v.title}
                    </p>
                  ))}
                  {preview.valid.length > 50 && (
                    <p className='text-xs text-muted-foreground'>... 외 {preview.valid.length - 50}건</p>
                  )}
                </div>
              </div>
            )}

            <DialogFooter className='mt-2'>
              <Button variant='outline' onClick={() => { reset(); onOpenChange(false) }}>취소</Button>
              <Button
                onClick={handleUpload}
                disabled={!preview || preview.valid.length === 0 || !!parseError || uploading}
              >
                <Upload className='mr-2 h-4 w-4' />
                {uploading ? '업로드 중...' : '업로드 시작'}
              </Button>
            </DialogFooter>
          </>
        )}

        {/* ── Step 2: 키워드 생성 중 ── */}
        {step === 'progress' && progress && (
          <>
            <DialogHeader>
              <DialogTitle>키워드 생성 중</DialogTitle>
              <DialogDescription>
                백그라운드에서 계속 처리됩니다. 닫아도 됩니다.
              </DialogDescription>
            </DialogHeader>

            <div className='flex flex-col gap-4 py-2'>
              {/* Progress bar */}
              <div className='flex flex-col gap-1.5'>
                <div className='flex justify-between text-sm'>
                  <span className='text-muted-foreground'>키워드 생성</span>
                  <span className='font-medium tabular-nums'>
                    {progress.processed} / {progress.total}
                    {progress.failed > 0 && (
                      <span className='text-destructive ml-1'>({progress.failed}건 실패)</span>
                    )}
                  </span>
                </div>
                <div className='w-full bg-muted rounded-full h-2.5 overflow-hidden'>
                  <div
                    className='bg-primary h-2.5 rounded-full transition-all duration-500'
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <p className='text-xs text-muted-foreground text-right'>{pct}%</p>
              </div>

              {/* Recent completed */}
              {progress.recent.length > 0 && (
                <div className='flex flex-col gap-1'>
                  <p className='text-xs font-medium text-muted-foreground'>최근 완료</p>
                  <div className='max-h-40 overflow-y-auto flex flex-col gap-1'>
                    {progress.recent.map((r) => (
                      <div key={r.id} className='flex items-center gap-2 text-sm'>
                        <CheckCircle2 className='h-3.5 w-3.5 text-green-500 shrink-0' />
                        <span className='truncate flex-1'>{r.title}</span>
                        <span className='text-xs text-muted-foreground shrink-0'>
                          키워드 {r.keyword_count}개
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <DialogFooter>
              <Button variant='outline' onClick={() => { stopPolling(); onOpenChange(false) }}>
                백그라운드로 전환
              </Button>
            </DialogFooter>
          </>
        )}

        {/* ── Step 3: 완료 ── */}
        {step === 'done' && progress && (
          <>
            <DialogHeader>
              <DialogTitle className='flex items-center gap-2'>
                <CheckCircle2 className='h-5 w-5 text-green-500' />
                키워드 생성 완료
              </DialogTitle>
            </DialogHeader>

            <div className='py-2 flex flex-col gap-2'>
              <div className='flex gap-2'>
                <Badge variant='default'>완료 {progress.processed}건</Badge>
                {progress.failed > 0 && (
                  <Badge variant='destructive'>실패 {progress.failed}건</Badge>
                )}
              </div>
            </div>

            <DialogFooter>
              <Button onClick={() => { reset(); onOpenChange(false) }}>닫기</Button>
            </DialogFooter>
          </>
        )}

      </DialogContent>
    </Dialog>
  )
}
