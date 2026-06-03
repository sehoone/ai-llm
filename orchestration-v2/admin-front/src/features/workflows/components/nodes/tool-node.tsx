import type { NodeProps } from '@xyflow/react'
import { Wrench } from 'lucide-react'
import { BaseNodeWrapper } from './base-node'
import type { ExecutionStatus } from '@/api/workflows'

const TOOL_LABELS: Record<string, string> = {
  web_search: '웹 검색',
}

interface ToolNodeData {
  tool?: string
  query?: string
  __status?: ExecutionStatus | 'skipped'
  [key: string]: unknown
}

export function ToolNode({ data, selected }: NodeProps) {
  const d = data as ToolNodeData
  const toolLabel = TOOL_LABELS[d.tool ?? 'web_search'] ?? d.tool ?? 'web_search'

  return (
    <BaseNodeWrapper selected={selected} status={d.__status}>
      <div className='px-3 py-2 border-b flex items-center gap-2'>
        <div className='p-1 rounded-md bg-rose-500/15'>
          <Wrench className='h-3.5 w-3.5 text-rose-600' />
        </div>
        <span className='text-xs font-semibold text-rose-700 dark:text-rose-400'>Tool</span>
        <span className='ml-auto text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded'>
          {toolLabel}
        </span>
      </div>
      <div className='px-3 py-2'>
        {d.query ? (
          <p className='text-[11px] text-muted-foreground font-mono line-clamp-2'>{d.query}</p>
        ) : (
          <p className='text-[11px] text-muted-foreground italic'>쿼리 미설정</p>
        )}
      </div>
    </BaseNodeWrapper>
  )
}
