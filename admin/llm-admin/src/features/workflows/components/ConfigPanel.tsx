'use client'

/* eslint-disable @typescript-eslint/no-explicit-any */
import { useCallback } from 'react'
import { X, Plus, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { cn } from '@/lib/utils'
import type { WorkflowNode } from '@/api/workflows'

interface ConfigPanelProps {
  node: WorkflowNode | null
  onUpdate: (nodeId: string, data: Record<string, any>) => void
  onClose: () => void
  className?: string
}

const LLM_MODELS = [
  'gpt-4o-mini',
  'gpt-4o',
  'gpt-5-mini',
  'gpt-5',
  'gpt-5-nano',
]

const CONDITION_OPERATORS = [
  { value: 'contains', label: 'contains' },
  { value: 'not_contains', label: 'not contains' },
  { value: 'equals', label: 'equals' },
  { value: 'not_equals', label: 'not equals' },
  { value: 'starts_with', label: 'starts with' },
  { value: 'ends_with', label: 'ends with' },
  { value: 'not_empty', label: 'is not empty' },
  { value: 'is_empty', label: 'is empty' },
  { value: 'greater_than', label: '>' },
  { value: 'less_than', label: '<' },
  { value: 'greater_than_or_equal', label: '>=' },
  { value: 'less_than_or_equal', label: '<=' },
]

export function ConfigPanel({ node, onUpdate, onClose, className }: ConfigPanelProps) {
  const update = useCallback(
    (patch: Record<string, any>) => {
      if (!node) return
      onUpdate(node.id, { ...node.data, ...patch })
    },
    [node, onUpdate]
  )

  if (!node) return null

  return (
    <aside className={cn('flex flex-col border-l bg-background', className)}>
      {/* Header */}
      <div className='px-4 py-3 border-b flex items-center justify-between'>
        <div>
          <p className='text-xs font-semibold uppercase tracking-wide text-muted-foreground'>
            {node.type}
          </p>
          <p className='text-sm font-medium capitalize'>{node.type} 설정</p>
        </div>
        <Button variant='ghost' size='icon' className='h-7 w-7' onClick={onClose}>
          <X className='h-4 w-4' />
        </Button>
      </div>

      {/* Node ID */}
      <div className='px-4 pt-3 pb-1'>
        <p className='text-[11px] text-muted-foreground font-mono'>id: {node.id}</p>
      </div>

      {/* Config content */}
      <div className='flex-1 overflow-y-auto px-4 py-3 space-y-5'>
        {node.type === 'start' && <StartConfig data={node.data} update={update} />}
        {node.type === 'end' && <EndConfig data={node.data} update={update} />}
        {node.type === 'llm' && <LLMConfig data={node.data} update={update} />}
        {node.type === 'condition' && <ConditionConfig data={node.data} update={update} />}
        {node.type === 'rag' && <RAGConfig data={node.data} update={update} />}
        {node.type === 'http' && <HTTPConfig data={node.data} update={update} />}
        {node.type === 'code' && <CodeConfig data={node.data} update={update} />}
        {node.type === 'tool' && <ToolConfig data={node.data} update={update} />}
        {node.type === 'loop' && <LoopConfig data={node.data} update={update} />}
      </div>
    </aside>
  )
}

// ── Start Node Config ─────────────────────────────────────────────────────────

function StartConfig({ data, update }: { data: any; update: (p: any) => void }) {
  const vars: any[] = data.variables ?? []

  const addVar = () =>
    update({ variables: [...vars, { name: '', type: 'string', required: false, description: '' }] })

  const removeVar = (i: number) =>
    update({ variables: vars.filter((_: any, idx: number) => idx !== i) })

  const patchVar = (i: number, patch: object) =>
    update({ variables: vars.map((v: any, idx: number) => (idx === i ? { ...v, ...patch } : v)) })

  return (
    <div className='space-y-4'>
      <div className='flex items-center justify-between'>
        <Label className='text-xs font-semibold'>입력 변수</Label>
        <Button size='sm' variant='outline' className='h-6 text-xs px-2' onClick={addVar}>
          <Plus className='h-3 w-3 mr-1' /> 추가
        </Button>
      </div>
      {vars.length === 0 && (
        <p className='text-[11px] text-muted-foreground italic text-center py-2'>
          변수를 추가해 워크플로우 입력을 정의하세요
        </p>
      )}
      {vars.map((v: any, i: number) => (
        <div key={i} className='space-y-2 p-3 border rounded-lg bg-muted/30 relative'>
          <Button
            size='icon'
            variant='ghost'
            className='h-5 w-5 absolute top-2 right-2 text-muted-foreground hover:text-destructive'
            onClick={() => removeVar(i)}
          >
            <Trash2 className='h-3 w-3' />
          </Button>
          <div className='grid grid-cols-2 gap-2'>
            <div className='space-y-1'>
              <Label className='text-[11px]'>Name</Label>
              <Input
                value={v.name}
                onChange={(e) => patchVar(i, { name: e.target.value })}
                placeholder='variable_name'
                className='h-7 text-xs font-mono'
              />
            </div>
            <div className='space-y-1'>
              <Label className='text-[11px]'>Type</Label>
              <Select value={v.type} onValueChange={(val) => patchVar(i, { type: val })}>
                <SelectTrigger className='h-7 text-xs'>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {['string', 'number', 'boolean', 'object'].map((t) => (
                    <SelectItem key={t} value={t} className='text-xs'>
                      {t}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className='space-y-1'>
            <Label className='text-[11px]'>Description (optional)</Label>
            <Input
              value={v.description ?? ''}
              onChange={(e) => patchVar(i, { description: e.target.value })}
              placeholder='What this variable is for'
              className='h-7 text-xs'
            />
          </div>
          <label className='flex items-center gap-2 cursor-pointer'>
            <input
              type='checkbox'
              checked={v.required ?? false}
              onChange={(e) => patchVar(i, { required: e.target.checked })}
              className='h-3.5 w-3.5'
            />
            <span className='text-[11px]'>Required</span>
          </label>
        </div>
      ))}
    </div>
  )
}

// ── End Node Config ───────────────────────────────────────────────────────────

function EndConfig({ data, update }: { data: any; update: (p: any) => void }) {
  const outputs: any[] = data.outputs ?? []

  const addOutput = () => update({ outputs: [...outputs, { name: '', value: '' }] })
  const removeOutput = (i: number) => update({ outputs: outputs.filter((_: any, idx: number) => idx !== i) })
  const patchOutput = (i: number, patch: object) =>
    update({ outputs: outputs.map((o: any, idx: number) => (idx === i ? { ...o, ...patch } : o)) })

  return (
    <div className='space-y-4'>
      <div className='flex items-center justify-between'>
        <Label className='text-xs font-semibold'>출력 변수</Label>
        <Button size='sm' variant='outline' className='h-6 text-xs px-2' onClick={addOutput}>
          <Plus className='h-3 w-3 mr-1' /> 추가
        </Button>
      </div>
      <p className='text-[11px] text-muted-foreground'>
        비어있으면 이전 노드의 출력을 그대로 전달합니다.
      </p>
      {outputs.map((o: any, i: number) => (
        <div key={i} className='space-y-2 p-3 border rounded-lg bg-muted/30 relative'>
          <Button
            size='icon'
            variant='ghost'
            className='h-5 w-5 absolute top-2 right-2 text-muted-foreground hover:text-destructive'
            onClick={() => removeOutput(i)}
          >
            <Trash2 className='h-3 w-3' />
          </Button>
          <div className='space-y-1'>
            <Label className='text-[11px]'>Name</Label>
            <Input
              value={o.name}
              onChange={(e) => patchOutput(i, { name: e.target.value })}
              placeholder='output_name'
              className='h-7 text-xs font-mono'
            />
          </div>
          <div className='space-y-1'>
            <Label className='text-[11px]'>Value (template)</Label>
            <Input
              value={o.value}
              onChange={(e) => patchOutput(i, { value: e.target.value })}
              placeholder='{{nodes.llm-1.output.text}}'
              className='h-7 text-xs font-mono'
            />
          </div>
        </div>
      ))}
    </div>
  )
}

// ── LLM Node Config ───────────────────────────────────────────────────────────

function LLMConfig({ data, update }: { data: any; update: (p: any) => void }) {
  return (
    <div className='space-y-4'>
      <div className='space-y-1'>
        <Label className='text-xs font-semibold'>Model</Label>
        <Select value={data.model ?? 'gpt-4o-mini'} onValueChange={(v) => update({ model: v })}>
          <SelectTrigger className='text-xs h-8'>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {LLM_MODELS.map((m) => (
              <SelectItem key={m} value={m} className='text-xs'>
                {m}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className='space-y-1'>
        <Label className='text-xs font-semibold'>System Prompt</Label>
        <Textarea
          value={data.system_prompt ?? ''}
          onChange={(e) => update({ system_prompt: e.target.value })}
          placeholder='You are a helpful assistant.'
          className='text-xs font-mono resize-none min-h-[80px]'
        />
      </div>
      <div className='space-y-1'>
        <Label className='text-xs font-semibold'>
          Prompt <span className='text-muted-foreground font-normal'>(template)</span>
        </Label>
        <Textarea
          value={data.prompt ?? ''}
          onChange={(e) => update({ prompt: e.target.value })}
          placeholder={'User said: {{input.user_message}}\n\nPrevious: {{nodes.prev-node.output.text}}'}
          className='text-xs font-mono resize-none min-h-[120px]'
        />
        <p className='text-[11px] text-muted-foreground'>
          {'{{input.key}}'} / {'{{nodes.id.output.field}}'}
        </p>
      </div>
    </div>
  )
}

// ── RAG Node Config ───────────────────────────────────────────────────────────

function RAGConfig({ data, update }: { data: any; update: (p: any) => void }) {
  return (
    <div className='space-y-4'>
      <div className='space-y-1'>
        <Label className='text-xs font-semibold'>RAG Key</Label>
        <Input
          value={data.rag_key ?? ''}
          onChange={(e) => update({ rag_key: e.target.value })}
          placeholder='my-bot-knowledge'
          className='h-7 text-xs font-mono'
        />
      </div>
      <div className='space-y-1'>
        <Label className='text-xs font-semibold'>RAG Type</Label>
        <Select value={data.rag_type ?? 'chatbot_shared'} onValueChange={(v) => update({ rag_type: v })}>
          <SelectTrigger className='text-xs h-8'>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {['chatbot_shared', 'user_isolated', 'natural_search'].map((t) => (
              <SelectItem key={t} value={t} className='text-xs'>{t}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className='space-y-1'>
        <Label className='text-xs font-semibold'>Query <span className='font-normal text-muted-foreground'>(template)</span></Label>
        <Textarea
          value={data.query ?? ''}
          onChange={(e) => update({ query: e.target.value })}
          placeholder='{{input.user_question}}'
          className='text-xs font-mono resize-none min-h-[60px]'
        />
      </div>
      <div className='space-y-1'>
        <Label className='text-xs font-semibold'>Limit</Label>
        <Input
          type='number'
          value={data.limit ?? 5}
          onChange={(e) => update({ limit: Number(e.target.value) })}
          min={1}
          max={20}
          className='h-7 text-xs w-20'
        />
      </div>
      <div className='pt-2 border-t space-y-1'>
        <p className='text-[11px] font-semibold text-muted-foreground'>출력</p>
        <p className='text-[11px] text-muted-foreground font-mono'>{'{{nodes.id.output.text}}'} — 결합 텍스트</p>
        <p className='text-[11px] text-muted-foreground font-mono'>{'{{nodes.id.output.results}}'} — 청크 배열</p>
      </div>
    </div>
  )
}

// ── HTTP Node Config ──────────────────────────────────────────────────────────

function HTTPConfig({ data, update }: { data: any; update: (p: any) => void }) {
  const headers: Record<string, string> = data.headers ?? {}
  const headerEntries = Object.entries(headers)

  const updateHeaders = (entries: [string, string][]) =>
    update({ headers: Object.fromEntries(entries) })

  const addHeader = () => updateHeaders([...headerEntries, ['', '']])
  const removeHeader = (i: number) => updateHeaders(headerEntries.filter((_, idx) => idx !== i))
  const patchHeader = (i: number, key: string, val: string) => {
    const next = [...headerEntries]
    next[i] = [key, val]
    updateHeaders(next)
  }

  return (
    <div className='space-y-4'>
      <div className='grid grid-cols-3 gap-2'>
        <div className='space-y-1 col-span-1'>
          <Label className='text-xs font-semibold'>Method</Label>
          <Select value={data.method ?? 'GET'} onValueChange={(v) => update({ method: v })}>
            <SelectTrigger className='text-xs h-8'>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {['GET', 'POST', 'PUT', 'PATCH', 'DELETE'].map((m) => (
                <SelectItem key={m} value={m} className='text-xs font-mono'>{m}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className='space-y-1 col-span-2'>
          <Label className='text-xs font-semibold'>Timeout (s)</Label>
          <Input
            type='number'
            value={data.timeout ?? 30}
            onChange={(e) => update({ timeout: Number(e.target.value) })}
            min={1}
            max={120}
            className='h-8 text-xs'
          />
        </div>
      </div>
      <div className='space-y-1'>
        <Label className='text-xs font-semibold'>URL <span className='font-normal text-muted-foreground'>(template)</span></Label>
        <Input
          value={data.url ?? ''}
          onChange={(e) => update({ url: e.target.value })}
          placeholder='https://api.example.com/{{input.resource}}'
          className='h-7 text-xs font-mono'
        />
      </div>
      <div className='space-y-1'>
        <div className='flex items-center justify-between'>
          <Label className='text-xs font-semibold'>Headers</Label>
          <button onClick={addHeader} className='text-[11px] text-primary hover:underline'>+ 추가</button>
        </div>
        <div className='space-y-1.5'>
          {headerEntries.map(([k, v], i) => (
            <div key={i} className='flex gap-1 items-center'>
              <Input value={k} onChange={(e) => patchHeader(i, e.target.value, v)} placeholder='Key' className='h-6 text-xs flex-1 font-mono' />
              <Input value={v} onChange={(e) => patchHeader(i, k, e.target.value)} placeholder='Value' className='h-6 text-xs flex-1 font-mono' />
              <button onClick={() => removeHeader(i)} className='text-muted-foreground hover:text-destructive text-xs shrink-0'>✕</button>
            </div>
          ))}
        </div>
      </div>
      <div className='space-y-1'>
        <Label className='text-xs font-semibold'>Body <span className='font-normal text-muted-foreground'>(template, optional)</span></Label>
        <Textarea
          value={data.body ?? ''}
          onChange={(e) => update({ body: e.target.value })}
          placeholder={'{"key": "{{input.value}}"}'}
          className='text-xs font-mono resize-none min-h-[80px]'
        />
      </div>
    </div>
  )
}

// ── Code Node Config ──────────────────────────────────────────────────────────

function CodeConfig({ data, update }: { data: any; update: (p: any) => void }) {
  return (
    <div className='space-y-4'>
      <div className='space-y-1'>
        <Label className='text-xs font-semibold'>Python Code</Label>
        <Textarea
          value={data.code ?? ''}
          onChange={(e) => update({ code: e.target.value })}
          placeholder={
`# Available: input_data, nodes, json, re, math
# Must assign to 'result' (dict)

answer = nodes.get('llm-1', {}).get('text', '')
result = {
    'summary': answer[:200],
    'length': len(answer),
}`
          }
          className='text-xs font-mono resize-none min-h-[180px]'
        />
      </div>
      <div className='p-2.5 bg-muted/50 rounded-lg space-y-1'>
        <p className='text-[11px] font-semibold text-muted-foreground'>사용 가능한 변수</p>
        <p className='text-[11px] font-mono text-muted-foreground'>input_data — 워크플로우 입력</p>
        <p className='text-[11px] font-mono text-muted-foreground'>nodes — 이전 노드 출력 dict</p>
        <p className='text-[11px] font-mono text-muted-foreground'>json, re, math — 표준 모듈</p>
        <p className='text-[11px] font-mono text-red-500 mt-1'>⚠ 파일/네트워크/import 금지</p>
      </div>
    </div>
  )
}

// ── Tool Node Config ──────────────────────────────────────────────────────────

function ToolConfig({ data, update }: { data: any; update: (p: any) => void }) {
  return (
    <div className='space-y-4'>
      <div className='space-y-1'>
        <Label className='text-xs font-semibold'>Tool</Label>
        <Select value={data.tool ?? 'web_search'} onValueChange={(v) => update({ tool: v })}>
          <SelectTrigger className='text-xs h-8'>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value='web_search' className='text-xs'>web_search — DuckDuckGo</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div className='space-y-1'>
        <Label className='text-xs font-semibold'>Query <span className='font-normal text-muted-foreground'>(template)</span></Label>
        <Textarea
          value={data.query ?? ''}
          onChange={(e) => update({ query: e.target.value })}
          placeholder='{{input.search_term}}'
          className='text-xs font-mono resize-none min-h-[60px]'
        />
      </div>
      <div className='pt-2 border-t'>
        <p className='text-[11px] font-semibold text-muted-foreground mb-1'>출력</p>
        <p className='text-[11px] text-muted-foreground font-mono'>{'{{nodes.id.output.results}}'} — 검색 결과 텍스트</p>
      </div>
    </div>
  )
}

// ── Loop Node Config ──────────────────────────────────────────────────────────

function LoopConfig({ data, update }: { data: any; update: (p: any) => void }) {
  const processor = data.processor ?? 'passthrough'
  return (
    <div className='space-y-4'>
      <div className='space-y-1'>
        <Label className='text-xs font-semibold'>Items Source <span className='font-normal text-muted-foreground'>(template)</span></Label>
        <Input
          value={data.items ?? ''}
          onChange={(e) => update({ items: e.target.value })}
          placeholder='{{nodes.rag-1.output.results}}'
          className='h-7 text-xs font-mono'
        />
        <p className='text-[11px] text-muted-foreground'>배열을 반환하는 템플릿 표현식</p>
      </div>
      <div className='space-y-1'>
        <Label className='text-xs font-semibold'>Item Variable Name</Label>
        <Input
          value={data.item_var ?? 'item'}
          onChange={(e) => update({ item_var: e.target.value })}
          placeholder='item'
          className='h-7 text-xs font-mono'
        />
        <p className='text-[11px] text-muted-foreground'>각 항목을 참조할 때 사용: {'{{item}}'} 또는 {'{{item.field}}'}</p>
      </div>
      <div className='space-y-1'>
        <Label className='text-xs font-semibold'>Processor</Label>
        <Select value={processor} onValueChange={(v) => update({ processor: v })}>
          <SelectTrigger className='text-xs h-8'><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value='passthrough' className='text-xs'>passthrough — 항목 그대로</SelectItem>
            <SelectItem value='llm' className='text-xs'>llm — LLM 처리</SelectItem>
            <SelectItem value='http' className='text-xs'>http — HTTP 호출</SelectItem>
          </SelectContent>
        </Select>
      </div>
      {processor === 'llm' && (
        <>
          <div className='space-y-1'>
            <Label className='text-xs font-semibold'>Model</Label>
            <Select value={data.model ?? 'gpt-4o-mini'} onValueChange={(v) => update({ model: v })}>
              <SelectTrigger className='text-xs h-8'><SelectValue /></SelectTrigger>
              <SelectContent>
                {LLM_MODELS.map((m) => <SelectItem key={m} value={m} className='text-xs'>{m}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className='space-y-1'>
            <Label className='text-xs font-semibold'>System Prompt</Label>
            <Textarea value={data.system_prompt ?? ''} onChange={(e) => update({ system_prompt: e.target.value })}
              placeholder='You are a helpful assistant.' className='text-xs font-mono resize-none min-h-[60px]' />
          </div>
          <div className='space-y-1'>
            <Label className='text-xs font-semibold'>Prompt <span className='font-normal text-muted-foreground'>(template)</span></Label>
            <Textarea value={data.prompt ?? ''} onChange={(e) => update({ prompt: e.target.value })}
              placeholder={'Summarize: {{item.content}}'} className='text-xs font-mono resize-none min-h-[80px]' />
          </div>
        </>
      )}
      {processor === 'http' && (
        <>
          <div className='grid grid-cols-2 gap-2'>
            <div className='space-y-1'>
              <Label className='text-xs font-semibold'>Method</Label>
              <Select value={data.method ?? 'GET'} onValueChange={(v) => update({ method: v })}>
                <SelectTrigger className='text-xs h-8'><SelectValue /></SelectTrigger>
                <SelectContent>
                  {['GET', 'POST', 'PUT', 'PATCH', 'DELETE'].map((m) =>
                    <SelectItem key={m} value={m} className='text-xs font-mono'>{m}</SelectItem>
                  )}
                </SelectContent>
              </Select>
            </div>
            <div className='space-y-1'>
              <Label className='text-xs font-semibold'>Timeout (s)</Label>
              <Input type='number' value={data.timeout ?? 30}
                onChange={(e) => update({ timeout: Number(e.target.value) })}
                min={1} max={120} className='h-8 text-xs' />
            </div>
          </div>
          <div className='space-y-1'>
            <Label className='text-xs font-semibold'>URL <span className='font-normal text-muted-foreground'>(template)</span></Label>
            <Input value={data.url ?? ''} onChange={(e) => update({ url: e.target.value })}
              placeholder='https://api.example.com/{{item.id}}' className='h-7 text-xs font-mono' />
          </div>
          <div className='space-y-1'>
            <Label className='text-xs font-semibold'>Body <span className='font-normal text-muted-foreground'>(optional)</span></Label>
            <Textarea value={data.body ?? ''} onChange={(e) => update({ body: e.target.value })}
              placeholder={'{"id": "{{item.id}}"}'} className='text-xs font-mono resize-none min-h-[60px]' />
          </div>
        </>
      )}
      <div className='pt-2 border-t space-y-1'>
        <p className='text-[11px] font-semibold text-muted-foreground'>출력</p>
        <p className='text-[11px] font-mono text-muted-foreground'>{'{{nodes.id.output.results}}'} — 처리 결과 배열</p>
        <p className='text-[11px] font-mono text-muted-foreground'>{'{{nodes.id.output.count}}'} — 처리된 항목 수</p>
      </div>
    </div>
  )
}

// ── Condition Node Config ─────────────────────────────────────────────────────

function ConditionConfig({ data, update }: { data: any; update: (p: any) => void }) {
  return (
    <div className='space-y-4'>
      <div className='space-y-1'>
        <Label className='text-xs font-semibold'>Left Operand</Label>
        <Input
          value={data.left ?? ''}
          onChange={(e) => update({ left: e.target.value })}
          placeholder='{{nodes.llm-1.output.text}}'
          className='h-7 text-xs font-mono'
        />
      </div>
      <div className='space-y-1'>
        <Label className='text-xs font-semibold'>Operator</Label>
        <Select value={data.operator ?? 'not_empty'} onValueChange={(v) => update({ operator: v })}>
          <SelectTrigger className='text-xs h-8'>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {CONDITION_OPERATORS.map((op) => (
              <SelectItem key={op.value} value={op.value} className='text-xs'>
                {op.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className='space-y-1'>
        <Label className='text-xs font-semibold'>
          Right Operand <span className='text-muted-foreground font-normal'>(optional)</span>
        </Label>
        <Input
          value={data.right ?? ''}
          onChange={(e) => update({ right: e.target.value })}
          placeholder='yes'
          className='h-7 text-xs font-mono'
        />
      </div>
      <div className='pt-2 border-t space-y-1'>
        <p className='text-[11px] font-semibold text-muted-foreground'>연결 핸들</p>
        <p className='text-[11px] text-green-600'>● true → 조건 충족 시</p>
        <p className='text-[11px] text-red-500'>● false → 조건 불충족 시</p>
      </div>
    </div>
  )
}
