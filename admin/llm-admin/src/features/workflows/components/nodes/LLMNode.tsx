import type { NodeProps } from '@xyflow/react'
import { Sparkles } from 'lucide-react'
import { BaseNodeWrapper } from './BaseNode'
import type { ExecutionStatus } from '@/api/workflows'

interface LLMNodeData {
  model?: string
  system_prompt?: string
  prompt?: string
  __status?: ExecutionStatus | 'skipped'
  [key: string]: unknown
}

export function LLMNode({ data, selected }: NodeProps) {
  const d = data as LLMNodeData

  return (
    <BaseNodeWrapper selected={selected} status={d.__status}>
      <div className='px-3 py-2 border-b flex items-center gap-2'>
        <div className='p-1 rounded-md bg-purple-500/15'>
          <Sparkles className='h-3.5 w-3.5 text-purple-600' />
        </div>
        <span className='text-xs font-semibold text-purple-700 dark:text-purple-400'>LLM</span>
        {d.model && (
          <span className='ml-auto text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded'>
            {d.model}
          </span>
        )}
      </div>
      <div className='px-3 py-2'>
        {d.prompt ? (
          <p className='text-[11px] text-muted-foreground line-clamp-3 font-mono leading-relaxed'>
            {d.prompt}
          </p>
        ) : (
          <p className='text-[11px] text-muted-foreground italic'>No prompt configured</p>
        )}
      </div>
    </BaseNodeWrapper>
  )
}
