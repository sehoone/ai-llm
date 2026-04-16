import type { NodeProps } from '@xyflow/react'
import { Database } from 'lucide-react'
import { BaseNodeWrapper } from './BaseNode'
import type { ExecutionStatus } from '@/api/workflows'

interface RAGNodeData {
  rag_key?: string
  rag_type?: string
  query?: string
  limit?: number
  __status?: ExecutionStatus | 'skipped'
  [key: string]: unknown
}

export function RAGNode({ data, selected }: NodeProps) {
  const d = data as RAGNodeData

  return (
    <BaseNodeWrapper selected={selected} status={d.__status}>
      <div className='px-3 py-2 border-b flex items-center gap-2'>
        <div className='p-1 rounded-md bg-cyan-500/15'>
          <Database className='h-3.5 w-3.5 text-cyan-600' />
        </div>
        <span className='text-xs font-semibold text-cyan-700 dark:text-cyan-400'>RAG</span>
        {d.rag_key && (
          <span className='ml-auto text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded font-mono truncate max-w-[90px]'>
            {d.rag_key}
          </span>
        )}
      </div>
      <div className='px-3 py-2'>
        {d.query ? (
          <p className='text-[11px] text-muted-foreground line-clamp-2 font-mono'>{d.query}</p>
        ) : (
          <p className='text-[11px] text-muted-foreground italic'>쿼리 미설정</p>
        )}
        <p className='text-[10px] text-muted-foreground mt-1'>
          {d.rag_type ?? 'chatbot_shared'} · limit {d.limit ?? 5}
        </p>
      </div>
    </BaseNodeWrapper>
  )
}
