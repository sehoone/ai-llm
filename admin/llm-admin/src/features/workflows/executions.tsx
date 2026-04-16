'use client'

/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  CheckCircle2, XCircle, Loader2, Clock, ArrowLeft,
  ChevronDown, ChevronRight, SkipForward,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Header } from '@/components/layout/header'
import { Main } from '@/components/layout/main'
import { workflowApi, type WorkflowExecution, type ExecutionListItem, type NodeExecution } from '@/api/workflows'
import { toast } from 'sonner'
import { logger } from '@/lib/logger'
import { formatDistanceToNow, format } from 'date-fns'
import { ko } from 'date-fns/locale'
import { cn } from '@/lib/utils'

// ── Status helpers ────────────────────────────────────────────────────────────

function StatusIcon({ status, className }: { status: string; className?: string }) {
  if (status === 'completed') return <CheckCircle2 className={cn('h-4 w-4 text-green-500', className)} />
  if (status === 'failed') return <XCircle className={cn('h-4 w-4 text-red-500', className)} />
  if (status === 'running') return <Loader2 className={cn('h-4 w-4 text-blue-500 animate-spin', className)} />
  if (status === 'skipped') return <SkipForward className={cn('h-4 w-4 text-muted-foreground', className)} />
  return <Clock className={cn('h-4 w-4 text-muted-foreground', className)} />
}

function StatusBadge({ status }: { status: string }) {
  const variants: Record<string, string> = {
    completed: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    failed: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    running: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    pending: 'bg-muted text-muted-foreground',
  }
  return (
    <span className={cn('text-[10px] font-semibold px-2 py-0.5 rounded-full', variants[status] ?? variants.pending)}>
      {status}
    </span>
  )
}

function duration(start: string, end: string | null): string {
  if (!end) return '–'
  const ms = new Date(end).getTime() - new Date(start).getTime()
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

// ── Node Execution Row ────────────────────────────────────────────────────────

function NodeRow({ ne }: { ne: NodeExecution }) {
  const [expanded, setExpanded] = useState(false)
  const hasDetail = ne.output_data || ne.error || ne.input_data

  return (
    <div className='border rounded-lg overflow-hidden'>
      <button
        className='w-full flex items-center gap-3 px-4 py-2.5 hover:bg-muted/40 transition-colors text-left'
        onClick={() => hasDetail && setExpanded((p) => !p)}
      >
        <StatusIcon status={ne.status} className='shrink-0 h-3.5 w-3.5' />
        <span className='text-xs font-mono text-muted-foreground w-28 shrink-0 truncate'>{ne.node_id}</span>
        <Badge variant='outline' className='text-[10px] h-4 px-1.5 shrink-0'>{ne.node_type}</Badge>
        <span className='ml-auto text-[11px] text-muted-foreground shrink-0'>
          {duration(ne.created_at, ne.completed_at)}
        </span>
        {hasDetail && (
          expanded
            ? <ChevronDown className='h-3.5 w-3.5 text-muted-foreground shrink-0' />
            : <ChevronRight className='h-3.5 w-3.5 text-muted-foreground shrink-0' />
        )}
      </button>
      {expanded && (
        <div className='border-t bg-muted/20 px-4 py-3 space-y-3'>
          {ne.error && (
            <div>
              <p className='text-[11px] font-semibold text-red-500 mb-1'>오류</p>
              <pre className='text-[11px] font-mono text-red-500 whitespace-pre-wrap break-all'>{ne.error}</pre>
            </div>
          )}
          {ne.input_data && Object.keys(ne.input_data).length > 0 && (
            <div>
              <p className='text-[11px] font-semibold text-muted-foreground mb-1'>입력</p>
              <pre className='text-[11px] font-mono whitespace-pre-wrap break-all text-foreground/80'>
                {JSON.stringify(ne.input_data, null, 2)}
              </pre>
            </div>
          )}
          {ne.output_data && (
            <div>
              <p className='text-[11px] font-semibold text-muted-foreground mb-1'>출력</p>
              <pre className='text-[11px] font-mono whitespace-pre-wrap break-all text-foreground/80'>
                {JSON.stringify(ne.output_data, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Execution Detail Modal ────────────────────────────────────────────────────

function ExecutionDetail({ execution }: { execution: WorkflowExecution }) {
  return (
    <div className='space-y-4'>
      {/* Summary row */}
      <div className='flex items-center gap-4 p-4 border rounded-xl bg-card'>
        <StatusIcon status={execution.status} className='h-5 w-5' />
        <div>
          <p className='text-sm font-semibold'>{execution.id.slice(0, 8)}…</p>
          <p className='text-[11px] text-muted-foreground'>
            {format(new Date(execution.created_at), 'yyyy-MM-dd HH:mm:ss')}
            {' · '}
            {duration(execution.created_at, execution.completed_at)}
          </p>
        </div>
        <StatusBadge status={execution.status} />
      </div>

      {/* Error */}
      {execution.error && (
        <div className='p-3 border border-red-200 dark:border-red-800 rounded-lg bg-red-50 dark:bg-red-950/20'>
          <p className='text-xs font-semibold text-red-600 mb-1'>실행 오류</p>
          <pre className='text-[11px] font-mono text-red-600 whitespace-pre-wrap'>{execution.error}</pre>
        </div>
      )}

      {/* Final output */}
      {execution.output_data && (
        <div className='p-3 border rounded-lg'>
          <p className='text-xs font-semibold text-muted-foreground mb-2'>최종 출력</p>
          <pre className='text-[11px] font-mono whitespace-pre-wrap break-all'>
            {JSON.stringify(execution.output_data, null, 2)}
          </pre>
        </div>
      )}

      {/* Node executions */}
      {execution.node_executions.length > 0 && (
        <div className='space-y-2'>
          <p className='text-xs font-semibold text-muted-foreground'>노드별 실행 ({execution.node_executions.length})</p>
          {execution.node_executions.map((ne) => (
            <NodeRow key={ne.id} ne={ne} />
          ))}
        </div>
      )}
    </div>
  )
}

// ── Main Executions Page ──────────────────────────────────────────────────────

interface ExecutionsProps {
  workflowId: string
}

export function WorkflowExecutions({ workflowId }: ExecutionsProps) {
  const router = useRouter()
  const [list, setList] = useState<ExecutionListItem[]>([])
  const [selected, setSelected] = useState<WorkflowExecution | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingDetail, setLoadingDetail] = useState(false)

  useEffect(() => {
    workflowApi.listExecutions(workflowId).then((data) => {
      setList(data)
      if (data.length > 0) loadDetail(data[0].id)
    }).catch((err) => {
      logger.error('Failed to load executions', err)
      toast.error('실행 목록 로드 실패')
    }).finally(() => setLoading(false))
  }, [workflowId])

  const loadDetail = async (execId: string) => {
    setLoadingDetail(true)
    try {
      const detail = await workflowApi.getExecution(execId)
      setSelected(detail)
    } catch (err) {
      logger.error('Failed to load execution detail', err)
      toast.error('실행 상세 로드 실패')
    } finally {
      setLoadingDetail(false)
    }
  }

  return (
    <>
      <Header fixed>
        <Button variant='ghost' size='sm' onClick={() => router.push(`/workflows/${workflowId}/edit`)}>
          <ArrowLeft className='h-4 w-4 mr-1' /> 에디터로
        </Button>
        <span className='text-sm font-medium ml-3'>실행 히스토리</span>
      </Header>

      <Main className='flex gap-6 overflow-hidden'>
        {/* Left: execution list */}
        <div className='w-72 shrink-0 flex flex-col gap-2'>
          <p className='text-xs font-semibold text-muted-foreground'>
            전체 실행 {list.length}건
          </p>
          {loading && <p className='text-sm text-muted-foreground'>로딩 중...</p>}
          {list.map((exec) => (
            <button
              key={exec.id}
              onClick={() => loadDetail(exec.id)}
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-xl border text-left hover:bg-muted/50 transition-colors',
                selected?.id === exec.id && 'border-primary bg-primary/5'
              )}
            >
              <StatusIcon status={exec.status} className='shrink-0' />
              <div className='min-w-0'>
                <p className='text-xs font-mono text-muted-foreground truncate'>{exec.id.slice(0, 12)}…</p>
                <p className='text-[11px] text-muted-foreground'>
                  {formatDistanceToNow(new Date(exec.created_at), { addSuffix: true, locale: ko })}
                </p>
              </div>
              <StatusBadge status={exec.status} />
            </button>
          ))}
          {!loading && list.length === 0 && (
            <p className='text-sm text-muted-foreground text-center py-8'>실행 기록 없음</p>
          )}
        </div>

        {/* Right: execution detail */}
        <div className='flex-1 overflow-y-auto'>
          {loadingDetail && (
            <div className='flex items-center justify-center py-16 text-muted-foreground'>
              <Loader2 className='h-5 w-5 animate-spin mr-2' /> 로딩 중...
            </div>
          )}
          {!loadingDetail && selected && <ExecutionDetail execution={selected} />}
          {!loadingDetail && !selected && !loading && (
            <div className='text-center py-16 text-muted-foreground text-sm'>
              좌측에서 실행을 선택하세요
            </div>
          )}
        </div>
      </Main>
    </>
  )
}
