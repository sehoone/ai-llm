import type { NodeProps } from '@xyflow/react'
import { GitBranch } from 'lucide-react'
import { BaseNodeWrapper } from './BaseNode'
import type { ExecutionStatus } from '@/api/workflows'

interface ConditionNodeData {
  left?: string
  operator?: string
  right?: string
  __status?: ExecutionStatus | 'skipped'
  [key: string]: unknown
}

export function ConditionNode({ data, selected }: NodeProps) {
  const d = data as ConditionNodeData

  return (
    <BaseNodeWrapper selected={selected} status={d.__status} conditionOutputs>
      <div className='px-3 py-2 border-b flex items-center gap-2'>
        <div className='p-1 rounded-md bg-amber-500/15'>
          <GitBranch className='h-3.5 w-3.5 text-amber-600' />
        </div>
        <span className='text-xs font-semibold text-amber-700 dark:text-amber-400'>Condition</span>
      </div>
      <div className='px-3 py-2 space-y-1'>
        <div className='text-[11px] font-mono text-muted-foreground truncate'>
          {d.left || <span className='italic'>left operand</span>}
        </div>
        <div className='text-[11px] font-semibold text-foreground text-center'>
          {d.operator || 'not_empty'}
        </div>
        {d.right && (
          <div className='text-[11px] font-mono text-muted-foreground truncate'>{d.right}</div>
        )}
        {/* Branch labels */}
        <div className='flex justify-end flex-col items-end gap-2 pt-1'>
          <span className='text-[10px] text-green-600 font-medium'>true ↗</span>
          <span className='text-[10px] text-red-500 font-medium'>false ↘</span>
        </div>
      </div>
    </BaseNodeWrapper>
  )
}
