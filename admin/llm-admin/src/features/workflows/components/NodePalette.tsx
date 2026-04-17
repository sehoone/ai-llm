import { Play, Square, Sparkles, GitBranch, Database, Globe, Code2, Wrench, Repeat2 } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface PaletteNode {
  type: string
  label: string
  description: string
  icon: React.ReactNode
  color: string
  group: string
}

export const PALETTE_NODES: PaletteNode[] = [
  // ── Flow ─────────────────────────────────────────────────────────────────
  {
    type: 'start',
    label: 'Start',
    description: '워크플로우 시작 & 입력 변수',
    icon: <Play className='h-4 w-4' fill='currentColor' />,
    color: 'text-green-600 bg-green-500/10 border-green-200 dark:border-green-800',
    group: 'Flow',
  },
  {
    type: 'end',
    label: 'End',
    description: '워크플로우 종료 & 출력 수집',
    icon: <Square className='h-4 w-4' fill='currentColor' />,
    color: 'text-orange-600 bg-orange-500/10 border-orange-200 dark:border-orange-800',
    group: 'Flow',
  },
  {
    type: 'condition',
    label: 'Condition',
    description: '조건 분기 (if / else)',
    icon: <GitBranch className='h-4 w-4' />,
    color: 'text-amber-600 bg-amber-500/10 border-amber-200 dark:border-amber-800',
    group: 'Flow',
  },
  // ── AI ───────────────────────────────────────────────────────────────────
  {
    type: 'llm',
    label: 'LLM',
    description: 'AI 모델 호출',
    icon: <Sparkles className='h-4 w-4' />,
    color: 'text-purple-600 bg-purple-500/10 border-purple-200 dark:border-purple-800',
    group: 'AI',
  },
  {
    type: 'rag',
    label: 'RAG',
    description: '지식베이스 의미 검색',
    icon: <Database className='h-4 w-4' />,
    color: 'text-cyan-600 bg-cyan-500/10 border-cyan-200 dark:border-cyan-800',
    group: 'AI',
  },
  {
    type: 'tool',
    label: 'Tool',
    description: '내장 도구 (웹 검색 등)',
    icon: <Wrench className='h-4 w-4' />,
    color: 'text-rose-600 bg-rose-500/10 border-rose-200 dark:border-rose-800',
    group: 'AI',
  },
  {
    type: 'loop',
    label: 'Loop',
    description: '배열 반복 처리',
    icon: <Repeat2 className='h-4 w-4' />,
    color: 'text-violet-600 bg-violet-500/10 border-violet-200 dark:border-violet-800',
    group: 'Flow',
  },
  // ── Integration ──────────────────────────────────────────────────────────
  {
    type: 'http',
    label: 'HTTP',
    description: '외부 REST API 호출',
    icon: <Globe className='h-4 w-4' />,
    color: 'text-blue-600 bg-blue-500/10 border-blue-200 dark:border-blue-800',
    group: 'Integration',
  },
  {
    type: 'code',
    label: 'Code',
    description: 'Python 코드 실행',
    icon: <Code2 className='h-4 w-4' />,
    color: 'text-slate-600 bg-slate-500/10 border-slate-200 dark:border-slate-800',
    group: 'Integration',
  },
]

interface NodePaletteProps {
  className?: string
}

export function NodePalette({ className }: NodePaletteProps) {
  const onDragStart = (e: React.DragEvent, nodeType: string) => {
    e.dataTransfer.setData('application/workflow-node-type', nodeType)
    e.dataTransfer.effectAllowed = 'move'
  }

  return (
    <aside className={cn('flex flex-col border-r bg-background', className)}>
      <div className='px-4 py-3 border-b'>
        <p className='text-xs font-semibold text-muted-foreground uppercase tracking-wide'>Nodes</p>
      </div>
      <div className='flex-1 overflow-y-auto p-3'>
        {(['Flow', 'AI', 'Integration'] as const).map((group) => {
          const groupNodes = PALETTE_NODES.filter((n) => n.group === group)
          return (
            <div key={group} className='mb-4'>
              <p className='text-[10px] font-semibold text-muted-foreground uppercase tracking-wide mb-1.5 px-0.5'>
                {group}
              </p>
              <div className='space-y-1.5'>
                {groupNodes.map((node) => (
                  <div
                    key={node.type}
                    draggable
                    onDragStart={(e) => onDragStart(e, node.type)}
                    className={cn(
                      'flex items-center gap-2.5 p-2 rounded-lg border cursor-default active:cursor-move select-none',
                      'hover:shadow-sm transition-shadow',
                      node.color
                    )}
                  >
                    <div className='shrink-0'>{node.icon}</div>
                    <div className='min-w-0'>
                      <p className='text-xs font-semibold leading-none'>{node.label}</p>
                      <p className='text-[10px] text-muted-foreground mt-0.5 leading-tight'>{node.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )
        })}
      </div>
      <div className='px-4 py-3 border-t'>
        <p className='text-[11px] text-muted-foreground text-center'>드래그해서 캔버스에 추가</p>
      </div>
    </aside>
  )
}
