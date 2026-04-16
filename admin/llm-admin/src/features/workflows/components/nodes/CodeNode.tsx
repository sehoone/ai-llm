import type { NodeProps } from '@xyflow/react'
import { Code2 } from 'lucide-react'
import { BaseNodeWrapper } from './BaseNode'
import type { ExecutionStatus } from '@/api/workflows'

interface CodeNodeData {
  code?: string
  __status?: ExecutionStatus | 'skipped'
  [key: string]: unknown
}

export function CodeNode({ data, selected }: NodeProps) {
  const d = data as CodeNodeData
  const preview = d.code?.split('\n').slice(0, 3).join('\n')

  return (
    <BaseNodeWrapper selected={selected} status={d.__status}>
      <div className='px-3 py-2 border-b flex items-center gap-2'>
        <div className='p-1 rounded-md bg-slate-500/15'>
          <Code2 className='h-3.5 w-3.5 text-slate-600' />
        </div>
        <span className='text-xs font-semibold text-slate-700 dark:text-slate-300'>Code</span>
        <span className='ml-auto text-[10px] text-muted-foreground'>Python</span>
      </div>
      <div className='px-3 py-2'>
        {preview ? (
          <pre className='text-[10px] text-muted-foreground font-mono leading-relaxed line-clamp-3 whitespace-pre-wrap'>
            {preview}
          </pre>
        ) : (
          <p className='text-[11px] text-muted-foreground italic'>코드 미작성</p>
        )}
      </div>
    </BaseNodeWrapper>
  )
}
