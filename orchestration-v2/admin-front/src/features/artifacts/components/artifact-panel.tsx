'use client'

import { useEffect, useState } from 'react'

import { Check, Copy, Download, Loader2, Share2, X } from 'lucide-react'
import { toast } from 'sonner'

import { artifactService } from '@/api/artifacts'
import { logger } from '@/lib/logger'
import { useArtifactStore } from '@/stores/artifact-store'

import { ArtifactRenderer } from './artifact-renderer'
import { VersionSwitcher } from './version-switcher'

const TYPE_LABELS: Record<string, string> = {
  'text/html': 'HTML',
  'application/vnd.react': 'React',
  'image/svg+xml': 'SVG',
  'application/vnd.mermaid': 'Mermaid',
  'text/markdown': 'Markdown',
  'application/vnd.code': 'Code',
}

const TYPE_EXTENSIONS: Record<string, string> = {
  'text/html': 'html',
  'application/vnd.react': 'jsx',
  'image/svg+xml': 'svg',
  'application/vnd.mermaid': 'mmd',
  'text/markdown': 'md',
  'application/vnd.code': 'txt',
}

export function ArtifactPanel() {
  const { artifacts, activeId, close } = useArtifactStore()
  const active = activeId ? artifacts[activeId] : null

  const [copied, setCopied] = useState(false)
  const [publishing, setPublishing] = useState(false)
  // When viewing an older version, this overrides the live content.
  const [preview, setPreview] = useState<{ content: string; version: number } | null>(null)

  // Reset version preview when the active artifact or its live content changes.
  useEffect(() => {
    setPreview(null)
  }, [activeId, active?.content])

  if (!active) return null

  const displayContent = preview?.content ?? active.content
  const displayVersion = preview?.version ?? active.version

  const handleCopy = async () => {
    await navigator.clipboard.writeText(displayContent)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleDownload = () => {
    const ext = TYPE_EXTENSIONS[active.type] ?? 'txt'
    const blob = new Blob([displayContent], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${active.identifier}.${ext}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const handlePublish = async () => {
    if (!active.serverId) {
      toast.error('저장이 완료된 후 공유할 수 있습니다')
      return
    }
    setPublishing(true)
    try {
      const token = await artifactService.publish(active.serverId)
      const shareUrl = `${window.location.origin}/artifact/${token}`
      await navigator.clipboard.writeText(shareUrl)
      toast.success('공개 링크가 클립보드에 복사되었습니다')
    } catch (e) {
      logger.error('Failed to publish artifact', e)
      toast.error('공유 링크 생성에 실패했습니다')
    } finally {
      setPublishing(false)
    }
  }

  return (
    <div className='flex h-full flex-col overflow-hidden rounded-md border bg-card'>
      {/* Header */}
      <div className='flex flex-none items-center gap-2 border-b bg-background px-3 py-2'>
        <span className='rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground'>
          {TYPE_LABELS[active.type] ?? active.type}
        </span>
        <span className='truncate text-sm font-medium' title={active.title || active.identifier}>
          {active.title || active.identifier}
        </span>
        {active.isStreaming && <Loader2 className='h-3.5 w-3.5 animate-spin text-muted-foreground' />}

        <div className='ms-auto flex items-center gap-1'>
          {!active.isStreaming && (
            <VersionSwitcher
              serverId={active.serverId}
              currentVersion={active.version}
              onSelectVersion={(content, version) => setPreview({ content, version })}
            />
          )}
          <button
            type='button'
            onClick={handleCopy}
            title='복사'
            className='rounded p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground'
          >
            {copied ? <Check className='h-4 w-4 text-green-500' /> : <Copy className='h-4 w-4' />}
          </button>
          <button
            type='button'
            onClick={handleDownload}
            title='다운로드'
            className='rounded p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground'
          >
            <Download className='h-4 w-4' />
          </button>
          <button
            type='button'
            onClick={handlePublish}
            disabled={publishing || active.isStreaming}
            title='공유'
            className='rounded p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:opacity-40'
          >
            {publishing ? <Loader2 className='h-4 w-4 animate-spin' /> : <Share2 className='h-4 w-4' />}
          </button>
          <button
            type='button'
            onClick={close}
            title='닫기'
            className='rounded p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground'
          >
            <X className='h-4 w-4' />
          </button>
        </div>
      </div>

      {preview && (
        <div className='flex flex-none items-center justify-between bg-amber-500/10 px-3 py-1 text-xs text-amber-700 dark:text-amber-400'>
          <span>이전 버전 v{displayVersion} 미리보기 중</span>
          <button type='button' className='underline' onClick={() => setPreview(null)}>
            최신 버전으로
          </button>
        </div>
      )}

      {/* Body */}
      <div className='min-h-0 flex-1'>
        <ArtifactRenderer
          type={active.type}
          content={displayContent}
          // Always provide handlers: before the artifact is persisted (no serverId
          // yet, e.g. mid-stream) get() returns empty instead of erroring.
          dataGet={async () => (active.serverId ? artifactService.getData(active.serverId) : {})}
          dataSet={async (data) => {
            if (!active.serverId) {
              throw new Error('저장 준비 중입니다. 잠시 후 다시 시도해 주세요.')
            }
            await artifactService.setData(active.serverId, data)
          }}
        />
      </div>
    </div>
  )
}
