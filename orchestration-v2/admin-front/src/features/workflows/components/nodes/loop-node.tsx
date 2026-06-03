import type { NodeProps } from '@xyflow/react'
import { Repeat2 } from 'lucide-react'
import { BaseNodeWrapper } from './base-node'
import type { ExecutionStatus } from '@/api/workflows'

interface LoopNodeData {
  items?: string
  item_var?: string
  processor?: 'passthrough' | 'llm' | 'http'
  __status?: ExecutionStatus | 'skipped'
  [key: string]: unknown
}

export function LoopNode({ data, selected }: NodeProps) {
  const d = data as LoopNodeData
  const proc = d.processor ?? 'passthrough'

  return (
    <BaseNodeWrapper selected={selected} status={d.__status}>
      <div className='px-3 py-2 border-b flex items-center gap-2'>
        <div className='p-1 rounded-md bg-violet-500/15'>
          <Repeat2 className='h-3.5 w-3.5 text-violet-600' />
        </div>
        <span className='text-xs font-semibold text-violet-700 dark:text-violet-400'>Loop</span>
        <span className='ml-auto text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded capitalize'>
          {proc}
        </span>
      </div>
      <div className='px-3 py-2 space-y-1'>
        {d.items ? (
          <p className='text-[11px] text-muted-foreground font-mono truncate'>{d.items}</p>
        ) : (
          <p className='text-[11px] text-muted-foreground italic'>No items source</p>
        )}
        <p className='text-[10px] text-muted-foreground'>
          var: <span className='font-mono'>{d.item_var ?? 'item'}</span>
        </p>
      </div>
    </BaseNodeWrapper>
  )
}
