import type { NodeProps } from '@xyflow/react'
import { Play } from 'lucide-react'
import { BaseNodeWrapper } from './BaseNode'
import type { ExecutionStatus } from '@/api/workflows'

interface StartNodeData {
  label?: string
  variables?: { name: string; type: string; required?: boolean }[]
  __status?: ExecutionStatus | 'skipped'
  [key: string]: unknown
}

export function StartNode({ data, selected }: NodeProps) {
  const d = data as StartNodeData
  const vars: { name: string; type: string; required?: boolean }[] = d.variables ?? []

  return (
    <BaseNodeWrapper hasInput={false} selected={selected} status={d.__status}>
      <div className='px-3 py-2 border-b flex items-center gap-2'>
        <div className='p-1 rounded-md bg-green-500/15'>
          <Play className='h-3.5 w-3.5 text-green-600' fill='currentColor' />
        </div>
        <span className='text-xs font-semibold text-green-700 dark:text-green-400'>Start</span>
      </div>
      <div className='px-3 py-2 space-y-0.5'>
        {vars.length === 0 && (
          <p className='text-[11px] text-muted-foreground italic'>No input variables</p>
        )}
        {vars.map((v) => (
          <div key={v.name} className='flex items-center gap-1'>
            <span className='text-[11px] font-mono text-foreground'>{v.name}</span>
            <span className='text-[10px] text-muted-foreground'>:{v.type}</span>
            {v.required && <span className='text-[10px] text-red-500'>*</span>}
          </div>
        ))}
      </div>
    </BaseNodeWrapper>
  )
}
