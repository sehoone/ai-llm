import { Handle, Position } from '@xyflow/react'
import { cn } from '@/lib/utils'
import type { ExecutionStatus } from '@/api/workflows'

interface BaseNodeProps {
  children: React.ReactNode
  className?: string
  status?: ExecutionStatus | 'skipped'
  selected?: boolean
  hasInput?: boolean
  hasOutput?: boolean
  // condition nodes have two output handles
  conditionOutputs?: boolean
}

const STATUS_RING: Record<string, string> = {
  running: 'ring-2 ring-blue-500 ring-offset-1',
  completed: 'ring-2 ring-green-500 ring-offset-1',
  failed: 'ring-2 ring-red-500 ring-offset-1',
  skipped: 'opacity-40',
}

export function BaseNodeWrapper({
  children,
  className,
  status,
  selected,
  hasInput = true,
  hasOutput = true,
  conditionOutputs = false,
}: BaseNodeProps) {
  return (
    <div
      className={cn(
        'rounded-xl border bg-card text-card-foreground shadow-sm min-w-[200px] max-w-[260px]',
        selected && 'ring-2 ring-primary ring-offset-1',
        status && STATUS_RING[status],
        className
      )}
    >
      {hasInput && (
        <Handle
          type='target'
          position={Position.Left}
          className='!w-3 !h-3 !bg-muted-foreground !border-background !border-2'
        />
      )}
      {children}
      {hasOutput && !conditionOutputs && (
        <Handle
          type='source'
          position={Position.Right}
          className='!w-3 !h-3 !bg-muted-foreground !border-background !border-2'
        />
      )}
      {conditionOutputs && (
        <>
          <Handle
            type='source'
            id='true'
            position={Position.Right}
            style={{ top: '35%' }}
            className='!w-3 !h-3 !bg-green-500 !border-background !border-2'
          />
          <Handle
            type='source'
            id='false'
            position={Position.Right}
            style={{ top: '65%' }}
            className='!w-3 !h-3 !bg-red-500 !border-background !border-2'
          />
        </>
      )}
    </div>
  )
}
