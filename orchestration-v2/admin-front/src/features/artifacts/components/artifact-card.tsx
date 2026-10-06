'use client'

import { Globe, Trash2 } from 'lucide-react'

import { cn } from '@/lib/utils'
import type { ArtifactSummary } from '@/types/chat-api'

const TYPE_LABELS: Record<string, string> = {
  'text/html': 'HTML',
  'application/vnd.react': 'React',
  'image/svg+xml': 'SVG',
  'application/vnd.mermaid': 'Mermaid',
  'text/markdown': 'Markdown',
  'application/vnd.code': 'Code',
}

function formatWhen(iso: string): string {
  const d = new Date(iso)
  const diffMs = Date.now() - d.getTime()
  const min = Math.floor(diffMs / 60000)
  if (min < 1) return '방금'
  if (min < 60) return `${min}분 전`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr}시간 전`
  const day = Math.floor(hr / 24)
  if (day < 7) return `${day}일 전`
  return d.toLocaleDateString()
}

interface ArtifactCardProps {
  artifact: ArtifactSummary
  sessionName?: string
  selected?: boolean
  onClick: () => void
  onDelete: () => void
}

export function ArtifactCard({ artifact, sessionName, selected, onClick, onDelete }: ArtifactCardProps) {
  return (
    <div
      role='button'
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') onClick()
      }}
      className={cn(
        'group relative flex cursor-pointer flex-col gap-2 rounded-lg border p-3 transition-colors hover:bg-accent',
        selected ? 'border-primary bg-accent' : 'border-border'
      )}
    >
      <div className='flex items-center gap-2'>
        <span className='rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground'>
          {TYPE_LABELS[artifact.artifact_type] ?? artifact.artifact_type}
        </span>
        <span className='text-[10px] text-muted-foreground'>v{artifact.current_version}</span>
        {artifact.is_published && <Globe className='h-3 w-3 text-green-500' aria-label='공개됨' />}
        <button
          type='button'
          onClick={(e) => {
            e.stopPropagation()
            onDelete()
          }}
          title='삭제'
          className='ms-auto rounded p-1 text-muted-foreground opacity-0 transition-opacity hover:bg-destructive/10 hover:text-destructive group-hover:opacity-100'
        >
          <Trash2 className='h-3.5 w-3.5' />
        </button>
      </div>

      <div className='truncate text-sm font-medium' title={artifact.title || artifact.identifier}>
        {artifact.title || artifact.identifier}
      </div>

      <div className='flex items-center gap-1 text-[11px] text-muted-foreground'>
        <span>{formatWhen(artifact.updated_at)}</span>
        {sessionName && (
          <>
            <span>·</span>
            <span className='truncate' title={sessionName}>
              {sessionName}
            </span>
          </>
        )}
      </div>
    </div>
  )
}
