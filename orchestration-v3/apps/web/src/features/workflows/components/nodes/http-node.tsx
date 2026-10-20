import type { NodeProps } from '@xyflow/react'
import { Globe } from 'lucide-react'
import { BaseNodeWrapper } from './base-node'
import type { ExecutionStatus } from '@/api/workflows'

const METHOD_COLOR: Record<string, string> = {
  GET: 'text-green-600',
  POST: 'text-blue-600',
  PUT: 'text-yellow-600',
  PATCH: 'text-orange-600',
  DELETE: 'text-red-600',
}

interface HTTPNodeData {
  url?: string
  method?: string
  __status?: ExecutionStatus | 'skipped'
  [key: string]: unknown
}

export function HTTPNode({ data, selected }: NodeProps) {
  const d = data as HTTPNodeData
  const method = (d.method ?? 'GET').toUpperCase()

  return (
    <BaseNodeWrapper selected={selected} status={d.__status}>
      <div className='px-3 py-2 border-b flex items-center gap-2'>
        <div className='p-1 rounded-md bg-blue-500/15'>
          <Globe className='h-3.5 w-3.5 text-blue-600' />
        </div>
        <span className='text-xs font-semibold text-blue-700 dark:text-blue-400'>HTTP</span>
        <span className={`ml-auto text-[10px] font-bold ${METHOD_COLOR[method] ?? 'text-muted-foreground'}`}>
          {method}
        </span>
      </div>
      <div className='px-3 py-2'>
        {d.url ? (
          <p className='text-[11px] text-muted-foreground font-mono truncate'>{d.url}</p>
        ) : (
          <p className='text-[11px] text-muted-foreground italic'>URL 미설정</p>
        )}
      </div>
    </BaseNodeWrapper>
  )
}
