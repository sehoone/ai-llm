'use client'

/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useState } from 'react'
import { X, Copy, Plus, Trash2, Loader2, RefreshCw, ExternalLink } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { workflowApi, type Workflow, type WorkflowSchedule } from '@/api/workflows'
import { toast } from 'sonner'

interface SettingsDrawerProps {
  open: boolean
  workflow: Workflow | null
  onClose: () => void
  onWebhookChange: (token: string | null) => void
  className?: string
}

export function SettingsDrawer({ open, workflow, onClose, onWebhookChange, className }: SettingsDrawerProps) {
  const [webhookLoading, setWebhookLoading] = useState(false)
  const [schedules, setSchedules] = useState<WorkflowSchedule[]>([])
  const [schedulesLoading, setSchedulesLoading] = useState(false)
  const [newCron, setNewCron] = useState('')
  const [newLabel, setNewLabel] = useState('')
  const [addingSchedule, setAddingSchedule] = useState(false)

  useEffect(() => {
    if (open && workflow) {
      loadSchedules()
    }
  }, [open, workflow?.id])

  const loadSchedules = async () => {
    if (!workflow) return
    setSchedulesLoading(true)
    try {
      const data = await workflowApi.listSchedules(workflow.id)
      setSchedules(data)
    } catch {
      toast.error('스케줄 목록 로드 실패')
    } finally {
      setSchedulesLoading(false)
    }
  }

  const handleWebhook = async (action: 'generate' | 'revoke') => {
    if (!workflow) return
    setWebhookLoading(true)
    try {
      const { webhook_token } = await workflowApi.manageWebhook(workflow.id, action)
      onWebhookChange(webhook_token)
      toast.success(action === 'generate' ? 'Webhook 생성됨' : 'Webhook 삭제됨')
    } catch {
      toast.error('Webhook 처리 실패')
    } finally {
      setWebhookLoading(false)
    }
  }

  const handleAddSchedule = async () => {
    if (!workflow || !newCron.trim()) return
    setAddingSchedule(true)
    try {
      const s = await workflowApi.createSchedule(workflow.id, {
        label: newLabel,
        cron_expr: newCron.trim(),
        input_data: {},
      })
      setSchedules((prev) => [s, ...prev])
      setNewCron('')
      setNewLabel('')
      toast.success('스케줄 생성됨')
    } catch {
      toast.error('스케줄 생성 실패')
    } finally {
      setAddingSchedule(false)
    }
  }

  const handleToggleSchedule = async (s: WorkflowSchedule) => {
    if (!workflow) return
    try {
      const updated = await workflowApi.updateSchedule(workflow.id, s.id, { is_active: !s.is_active })
      setSchedules((prev) => prev.map((x) => (x.id === s.id ? updated : x)))
    } catch {
      toast.error('스케줄 수정 실패')
    }
  }

  const handleDeleteSchedule = async (s: WorkflowSchedule) => {
    if (!workflow) return
    try {
      await workflowApi.deleteSchedule(workflow.id, s.id)
      setSchedules((prev) => prev.filter((x) => x.id !== s.id))
      toast.success('스케줄 삭제됨')
    } catch {
      toast.error('스케줄 삭제 실패')
    }
  }

  const webhookUrl = workflow?.webhook_token
    ? `${process.env.NEXT_PUBLIC_API_URL ?? ''}/api/v1/webhooks/${workflow.webhook_token}`
    : null

  return (
    <div
      className={cn(
        'fixed inset-y-0 right-0 z-50 flex flex-col border-l bg-background shadow-xl transition-transform duration-300',
        open ? 'translate-x-0' : 'translate-x-full',
        className
      )}
    >
      {/* Header */}
      <div className='px-5 py-4 border-b flex items-center justify-between shrink-0'>
        <p className='text-sm font-semibold'>워크플로우 설정</p>
        <Button variant='ghost' size='icon' className='h-7 w-7' onClick={onClose}>
          <X className='h-4 w-4' />
        </Button>
      </div>

      {!workflow ? (
        <div className='flex-1 flex items-center justify-center text-sm text-muted-foreground p-6 text-center'>
          워크플로우를 먼저 저장하세요
        </div>
      ) : (
        <div className='flex-1 overflow-y-auto p-5 space-y-8'>
          {/* ── Webhook ────────────────────────────────────────────────────── */}
          <section className='space-y-3'>
            <div className='flex items-center gap-2'>
              <ExternalLink className='h-4 w-4 text-muted-foreground' />
              <p className='text-sm font-semibold'>Webhook 트리거</p>
              {workflow.webhook_token && (
                <Badge variant='secondary' className='text-[10px]'>활성</Badge>
              )}
            </div>
            <p className='text-[12px] text-muted-foreground'>
              외부에서 HTTP POST 요청으로 워크플로우를 실행합니다. 발행된 워크플로우에서만 동작합니다.
            </p>

            {webhookUrl && (
              <div className='flex gap-2 items-center'>
                <Input
                  value={webhookUrl}
                  readOnly
                  className='text-[11px] font-mono h-7 flex-1 bg-muted'
                />
                <Button
                  size='icon'
                  variant='ghost'
                  className='h-7 w-7 shrink-0'
                  onClick={() => { navigator.clipboard.writeText(webhookUrl); toast.success('복사됨') }}
                >
                  <Copy className='h-3.5 w-3.5' />
                </Button>
              </div>
            )}

            <div className='flex gap-2'>
              {!workflow.webhook_token ? (
                <Button
                  size='sm'
                  variant='outline'
                  onClick={() => handleWebhook('generate')}
                  disabled={webhookLoading}
                  className='text-xs'
                >
                  {webhookLoading ? <Loader2 className='h-3 w-3 animate-spin mr-1' /> : <Plus className='h-3 w-3 mr-1' />}
                  Webhook 생성
                </Button>
              ) : (
                <>
                  <Button
                    size='sm'
                    variant='outline'
                    onClick={() => handleWebhook('generate')}
                    disabled={webhookLoading}
                    className='text-xs'
                  >
                    {webhookLoading ? <Loader2 className='h-3 w-3 animate-spin mr-1' /> : <RefreshCw className='h-3 w-3 mr-1' />}
                    재생성
                  </Button>
                  <Button
                    size='sm'
                    variant='ghost'
                    onClick={() => handleWebhook('revoke')}
                    disabled={webhookLoading}
                    className='text-xs text-destructive hover:text-destructive'
                  >
                    삭제
                  </Button>
                </>
              )}
            </div>

            {webhookUrl && (
              <div className='text-[11px] text-muted-foreground bg-muted/50 rounded-lg p-3 space-y-1'>
                <p className='font-semibold'>예시:</p>
                <pre className='whitespace-pre-wrap break-all'>{`curl -X POST "${webhookUrl}" \\
  -H "Content-Type: application/json" \\
  -d '{"input_data": {"key": "value"}}'`}</pre>
              </div>
            )}
          </section>

          <div className='border-t' />

          {/* ── Schedules ──────────────────────────────────────────────────── */}
          <section className='space-y-3'>
            <p className='text-sm font-semibold'>스케줄 트리거</p>
            <p className='text-[12px] text-muted-foreground'>
              Cron 표현식으로 주기적 실행을 예약합니다 (UTC 기준).
            </p>

            {/* Add new schedule */}
            <div className='space-y-2 p-3 border rounded-lg bg-muted/30'>
              <p className='text-[11px] font-semibold text-muted-foreground'>새 스케줄</p>
              <Input
                value={newLabel}
                onChange={(e) => setNewLabel(e.target.value)}
                placeholder='라벨 (선택)'
                className='h-7 text-xs'
              />
              <div className='flex gap-2'>
                <Input
                  value={newCron}
                  onChange={(e) => setNewCron(e.target.value)}
                  placeholder='0 9 * * 1-5'
                  className='h-7 text-xs font-mono flex-1'
                />
                <Button
                  size='sm'
                  className='h-7 text-xs px-3'
                  onClick={handleAddSchedule}
                  disabled={addingSchedule || !newCron.trim()}
                >
                  {addingSchedule ? <Loader2 className='h-3 w-3 animate-spin' /> : <Plus className='h-3 w-3' />}
                </Button>
              </div>
              <p className='text-[10px] text-muted-foreground'>
                분 시 일 월 요일 — 예: <span className='font-mono'>0 9 * * 1-5</span> (평일 오전 9시)
              </p>
            </div>

            {/* Schedule list */}
            {schedulesLoading && (
              <div className='flex justify-center py-4'>
                <Loader2 className='h-4 w-4 animate-spin text-muted-foreground' />
              </div>
            )}
            {!schedulesLoading && schedules.length === 0 && (
              <p className='text-[12px] text-muted-foreground text-center py-3'>스케줄 없음</p>
            )}
            {schedules.map((s) => (
              <div key={s.id} className='flex items-center gap-3 p-3 border rounded-lg'>
                <div className='flex-1 min-w-0'>
                  {s.label && (
                    <p className='text-xs font-medium truncate'>{s.label}</p>
                  )}
                  <p className='text-[11px] font-mono text-muted-foreground'>{s.cron_expr}</p>
                </div>
                <label className='flex items-center gap-1.5 cursor-pointer shrink-0'>
                  <input
                    type='checkbox'
                    checked={s.is_active}
                    onChange={() => handleToggleSchedule(s)}
                    className='h-3.5 w-3.5'
                  />
                  <span className='text-[11px] text-muted-foreground'>{s.is_active ? '활성' : '비활성'}</span>
                </label>
                <Button
                  size='icon'
                  variant='ghost'
                  className='h-6 w-6 text-muted-foreground hover:text-destructive shrink-0'
                  onClick={() => handleDeleteSchedule(s)}
                >
                  <Trash2 className='h-3 w-3' />
                </Button>
              </div>
            ))}
          </section>
        </div>
      )}
    </div>
  )
}
