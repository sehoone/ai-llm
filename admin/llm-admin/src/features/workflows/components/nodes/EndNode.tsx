import type { NodeProps } from '@xyflow/react'
import { Square } from 'lucide-react'
import { BaseNodeWrapper } from './BaseNode'
import type { ExecutionStatus } from '@/api/workflows'

interface EndNodeData {
  outputs?: { name: string; value: string }[]
  __status?: ExecutionStatus | 'skipped'
  [key: string]: unknown
}

export function EndNode({ data, selected }: NodeProps) {
  const d = data as EndNodeData
  const outputs: { name: string; value: string }[] = d.outputs ?? []

  return (
    <BaseNodeWrapper hasOutput={false} selected={selected} status={d.__status}>
      <div className='px-3 py-2 border-b flex items-center gap-2'>
        <div className='p-1 rounded-md bg-orange-500/15'>
          <Square className='h-3.5 w-3.5 text-orange-600' fill='currentColor' />
        </div>
        <span className='text-xs font-semibold text-orange-700 dark:text-orange-400'>End</span>
      </div>
      <div className='px-3 py-2 space-y-0.5'>
        {outputs.length === 0 && (
          <p className='text-[11px] text-muted-foreground italic'>Pass-through output</p>
        )}
        {outputs.map((o) => (
          <div key={o.name} className='flex items-center gap-1'>
            <span className='text-[11px] font-mono text-foreground'>{o.name}</span>
            <span className='text-[10px] text-muted-foreground truncate max-w-[120px]'>{o.value}</span>
          </div>
        ))}
      </div>
    </BaseNodeWrapper>
  )
}
