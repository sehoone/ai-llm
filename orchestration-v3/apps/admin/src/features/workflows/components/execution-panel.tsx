'use client'

/* eslint-disable @typescript-eslint/no-explicit-any */
import { CheckCircle2, XCircle, Loader2, SkipForward, ChevronDown, ChevronUp } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { SSEEvent } from '@/api/workflows'

export interface ExecutionLog {
  id: string
  event: SSEEvent
  timestamp: Date
}

interface ExecutionPanelProps {
  logs: ExecutionLog[]
  isRunning: boolean
  finalOutput: Record<string, any> | null
  error: string | null
  className?: string
}

const EventIcon = ({ type }: { type: string }) => {
  if (type === 'node_start') return <Loader2 className='h-3.5 w-3.5 text-blue-500 animate-spin' />
  if (type === 'node_complete') return <CheckCircle2 className='h-3.5 w-3.5 text-green-500' />
  if (type === 'node_failed') return <XCircle className='h-3.5 w-3.5 text-red-500' />
  if (type === 'node_skipped') return <SkipForward className='h-3.5 w-3.5 text-muted-foreground' />
  if (type === 'execution_complete') return <CheckCircle2 className='h-3.5 w-3.5 text-green-600' />
  if (type === 'execution_failed') return <XCircle className='h-3.5 w-3.5 text-red-600' />
  return null
}

function formatEvent(e: SSEEvent): string {
  switch (e.type) {
    case 'node_start':
      return `[${e.node_type}] ${e.node_id} — 실행 시작`
    case 'node_complete':
      return `[${e.node_type}] ${e.node_id} — 완료`
    case 'node_failed':
      return `[${e.node_type}] ${e.node_id} — 실패: ${e.error}`
    case 'node_skipped':
      return `${e.node_id} — 스킵됨`
    case 'execution_complete':
      return `워크플로우 실행 완료`
    case 'execution_failed':
      return `워크플로우 실패: ${e.error}`
    default:
      return JSON.stringify(e)
  }
}

export function ExecutionPanel({ logs, isRunning, finalOutput, error, className }: ExecutionPanelProps) {
  const [collapsed, setCollapsed] = useState(false)

  const hasContent = logs.length > 0 || isRunning

  if (!hasContent && !error && !finalOutput) return null

  return (
    <div className={cn('border-t bg-background flex flex-col', collapsed ? 'h-10' : 'h-56', className)}>
      {/* Header */}
      <div
        className='flex items-center gap-2 px-4 py-2 cursor-pointer select-none border-b shrink-0'
        onClick={() => setCollapsed((p) => !p)}
      >
        {isRunning ? (
          <Loader2 className='h-3.5 w-3.5 text-blue-500 animate-spin' />
        ) : error ? (
          <XCircle className='h-3.5 w-3.5 text-red-500' />
        ) : finalOutput ? (
          <CheckCircle2 className='h-3.5 w-3.5 text-green-500' />
        ) : null}
        <span className='text-xs font-semibold'>실행 로그</span>
        {isRunning && <Badge variant='secondary' className='text-[10px] h-4 px-1.5'>Running</Badge>}
        <Button variant='ghost' size='icon' className='h-6 w-6 ml-auto'>
          {collapsed ? <ChevronUp className='h-3.5 w-3.5' /> : <ChevronDown className='h-3.5 w-3.5' />}
        </Button>
      </div>

      {!collapsed && (
        <div className='flex flex-1 overflow-hidden'>
          {/* Log stream */}
          <div className='flex-1 overflow-y-auto p-3 space-y-1 font-mono text-[11px]'>
            {logs.map((log) => (
              <div key={log.id} className='flex items-start gap-2'>
                <span className='text-muted-foreground shrink-0 mt-0.5'>
                  {log.timestamp.toLocaleTimeString()}
                </span>
                <EventIcon type={log.event.type} />
                <span className={cn(
                  log.event.type === 'node_failed' || log.event.type === 'execution_failed'
                    ? 'text-red-500'
                    : log.event.type === 'execution_complete'
                    ? 'text-green-600 font-semibold'
                    : 'text-foreground'
                )}>
                  {formatEvent(log.event)}
                </span>
              </div>
            ))}
            {isRunning && (
              <div className='flex items-center gap-2 text-muted-foreground'>
                <Loader2 className='h-3 w-3 animate-spin' />
                <span>실행 중...</span>
              </div>
            )}
          </div>

          {/* Final output panel */}
          {finalOutput && (
            <div className='w-72 border-l p-3 overflow-y-auto'>
              <p className='text-[11px] font-semibold text-muted-foreground mb-2'>최종 출력</p>
              <pre className='text-[11px] font-mono whitespace-pre-wrap break-all text-foreground'>
                {JSON.stringify(finalOutput, null, 2)}
              </pre>
            </div>
          )}
          {error && (
            <div className='w-72 border-l p-3 overflow-y-auto'>
              <p className='text-[11px] font-semibold text-red-500 mb-2'>오류</p>
              <pre className='text-[11px] font-mono whitespace-pre-wrap text-red-500'>{error}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
