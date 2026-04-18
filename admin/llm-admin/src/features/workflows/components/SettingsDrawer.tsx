'use client'

/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useState } from 'react'
import { X, Copy, Plus, Trash2, Loader2, RefreshCw, ExternalLink, Zap } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { cn } from '@/lib/utils'
import { workflowApi, type Workflow, type WorkflowSchedule, type WorkflowEndpoint } from '@/api/workflows'
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

  const [endpoints, setEndpoints] = useState<WorkflowEndpoint[]>([])
  const [endpointsLoading, setEndpointsLoading] = useState(false)
  const [newEpPath, setNewEpPath] = useState('')
  const [newEpMethod, setNewEpMethod] = useState('POST')
  const [newEpDesc, setNewEpDesc] = useState('')
  const [addingEndpoint, setAddingEndpoint] = useState(false)

  useEffect(() => {
    if (open && workflow) {
      loadSchedules()
      loadEndpoints()
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

  const loadEndpoints = async () => {
    if (!workflow) return
    setEndpointsLoading(true)
    try {
      const data = await workflowApi.listEndpoints(workflow.id)
      setEndpoints(data)
    } catch {
      toast.error('엔드포인트 목록 로드 실패')
    } finally {
      setEndpointsLoading(false)
    }
  }

  const handleAddEndpoint = async () => {
    if (!workflow || !newEpPath.trim()) return
    setAddingEndpoint(true)
    try {
      const ep = await workflowApi.createEndpoint(workflow.id, {
        path: newEpPath.trim(),
        method: newEpMethod,
        description: newEpDesc,
      })
      setEndpoints((prev) => [ep, ...prev])
      setNewEpPath('')
      setNewEpDesc('')
      toast.success('엔드포인트 생성됨')
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? '엔드포인트 생성 실패')
    } finally {
      setAddingEndpoint(false)
    }
  }

  const handleToggleEndpoint = async (ep: WorkflowEndpoint) => {
    if (!workflow) return
    try {
      const updated = await workflowApi.updateEndpoint(workflow.id, ep.id, { is_active: !ep.is_active })
      setEndpoints((prev) => prev.map((x) => (x.id === ep.id ? updated : x)))
    } catch {
      toast.error('엔드포인트 수정 실패')
    }
  }

  const handleDeleteEndpoint = async (ep: WorkflowEndpoint) => {
    if (!workflow) return
    try {
      await workflowApi.deleteEndpoint(workflow.id, ep.id)
      setEndpoints((prev) => prev.filter((x) => x.id !== ep.id))
      toast.success('엔드포인트 삭제됨')
    } catch {
      toast.error('엔드포인트 삭제 실패')
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

          <div className='border-t' />

          {/* ── Dynamic API Endpoints ───────────────────────────────────────── */}
          <section className='space-y-3'>
            <div className='flex items-center gap-2'>
              <Zap className='h-4 w-4 text-muted-foreground' />
              <p className='text-sm font-semibold'>동적 API 엔드포인트</p>
            </div>
            <p className='text-[12px] text-muted-foreground'>
              커스텀 경로로 이 워크플로우를 HTTP API로 노출합니다.
              <br />
              prefix: <span className='font-mono'>/api/v1/run/</span>
            </p>

            {!workflow.is_published && (
              <div className='text-[11px] text-amber-600 bg-amber-50 dark:bg-amber-950/30 dark:text-amber-400 rounded-lg px-3 py-2'>
                발행되지 않은 워크플로우는 JWT 인증이 필요합니다.
              </div>
            )}

            {/* Add form */}
            <div className='space-y-2 p-3 border rounded-lg bg-muted/30'>
              <p className='text-[11px] font-semibold text-muted-foreground'>새 엔드포인트</p>
              <div className='flex gap-2'>
                <Select value={newEpMethod} onValueChange={setNewEpMethod}>
                  <SelectTrigger className='h-7 w-24 text-xs'>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {['GET', 'POST', 'PUT', 'PATCH', 'DELETE'].map((m) => (
                      <SelectItem key={m} value={m} className='text-xs'>{m}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Input
                  value={newEpPath}
                  onChange={(e) => setNewEpPath(e.target.value)}
                  placeholder='my-api/summarize'
                  className='h-7 text-xs font-mono flex-1'
                />
              </div>
              <Input
                value={newEpDesc}
                onChange={(e) => setNewEpDesc(e.target.value)}
                placeholder='설명 (선택)'
                className='h-7 text-xs'
              />
              <Button
                size='sm'
                className='h-7 text-xs w-full'
                onClick={handleAddEndpoint}
                disabled={addingEndpoint || !newEpPath.trim()}
              >
                {addingEndpoint ? <Loader2 className='h-3 w-3 animate-spin mr-1' /> : <Plus className='h-3 w-3 mr-1' />}
                엔드포인트 추가
              </Button>
            </div>

            {/* Endpoint list */}
            {endpointsLoading && (
              <div className='flex justify-center py-4'>
                <Loader2 className='h-4 w-4 animate-spin text-muted-foreground' />
              </div>
            )}
            {!endpointsLoading && endpoints.length === 0 && (
              <p className='text-[12px] text-muted-foreground text-center py-3'>엔드포인트 없음</p>
            )}
            {endpoints.map((ep) => {
              const fullUrl = `${process.env.NEXT_PUBLIC_API_URL ?? ''}/api/v1/run/${ep.path}`
              return (
                <div key={ep.id} className='border rounded-lg p-3 space-y-2'>
                  <div className='flex items-center gap-2'>
                    <Badge
                      variant='outline'
                      className={cn(
                        'text-[10px] font-mono px-1.5 shrink-0',
                        ep.method === 'GET' && 'text-green-600 border-green-300',
                        ep.method === 'POST' && 'text-blue-600 border-blue-300',
                        ep.method === 'PUT' && 'text-orange-600 border-orange-300',
                        ep.method === 'PATCH' && 'text-purple-600 border-purple-300',
                        ep.method === 'DELETE' && 'text-red-600 border-red-300',
                      )}
                    >
                      {ep.method}
                    </Badge>
                    <span className='text-[11px] font-mono truncate flex-1'>/run/{ep.path}</span>
                    <Button
                      size='icon'
                      variant='ghost'
                      className='h-6 w-6 shrink-0'
                      onClick={() => { navigator.clipboard.writeText(fullUrl); toast.success('복사됨') }}
                    >
                      <Copy className='h-3 w-3' />
                    </Button>
                    <Button
                      size='icon'
                      variant='ghost'
                      className='h-6 w-6 text-muted-foreground hover:text-destructive shrink-0'
                      onClick={() => handleDeleteEndpoint(ep)}
                    >
                      <Trash2 className='h-3 w-3' />
                    </Button>
                  </div>
                  {ep.description && (
                    <p className='text-[11px] text-muted-foreground'>{ep.description}</p>
                  )}
                  <div className='flex items-center justify-between'>
                    <label className='flex items-center gap-1.5 cursor-pointer'>
                      <input
                        type='checkbox'
                        checked={ep.is_active}
                        onChange={() => handleToggleEndpoint(ep)}
                        className='h-3.5 w-3.5'
                      />
                      <span className='text-[11px] text-muted-foreground'>{ep.is_active ? '활성' : '비활성'}</span>
                    </label>
                  </div>
                </div>
              )
            })}
          </section>
        </div>
      )}
    </div>
  )
}
