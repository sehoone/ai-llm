'use client'

import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { agentApi, type Agent, type RagKeyInfo, type RagGroupInfo } from '@/api/agents'
import { getChatModels, type ChatModel } from '@/api/llm-resources'
import { logger } from '@/lib/logger'
import { FileText, FolderOpen, X, Globe } from 'lucide-react'

const agentSchema = z.object({
  name: z.string().min(1, '이름을 입력하세요').max(100),
  description: z.string().max(500).optional(),
  system_prompt: z.string().optional(),
  welcome_message: z.string().optional(),
  model: z.string(),
  temperature: z.number().min(0).max(2),
  max_tokens: z.number().min(1).max(16000),
  rag_keys: z.array(z.string()),
  rag_groups: z.array(z.string()),
  rag_search_k: z.number().min(1).max(20),
  rag_enabled: z.boolean(),
  tools_enabled: z.array(z.string()),
  allowed_models: z.array(z.string()),
  is_published: z.boolean(),
})

type AgentFormData = z.infer<typeof agentSchema>

const AVAILABLE_TOOLS = [{ id: 'web_search', label: '웹 검색', icon: Globe }]

interface AgentFormProps {
  initial?: Agent
  onSubmit: (data: AgentFormData) => Promise<void>
  isLoading?: boolean
}

export function AgentForm({ initial, onSubmit, isLoading }: AgentFormProps) {
  const [ragKeys, setRagKeys] = useState<RagKeyInfo[]>([])
  const [ragGroups, setRagGroups] = useState<RagGroupInfo[]>([])
  const [chatModels, setChatModels] = useState<ChatModel[]>([])

  const { register, handleSubmit, watch, setValue, getValues, formState: { errors } } = useForm<AgentFormData>({
    resolver: zodResolver(agentSchema),
    defaultValues: {
      name: initial?.name ?? '',
      description: initial?.description ?? '',
      system_prompt: initial?.system_prompt ?? '',
      welcome_message: initial?.welcome_message ?? '',
      model: initial?.model ?? '',
      temperature: initial?.temperature ?? 0.7,
      max_tokens: initial?.max_tokens ?? 2000,
      rag_keys: initial?.rag_keys ?? [],
      rag_groups: initial?.rag_groups ?? [],
      rag_search_k: initial?.rag_search_k ?? 5,
      rag_enabled: initial?.rag_enabled ?? false,
      tools_enabled: initial?.tools_enabled ?? [],
      allowed_models: initial?.allowed_models ?? [],
      is_published: initial?.is_published ?? false,
    },
  })

  const watchedRagKeys = watch('rag_keys')
  const watchedRagGroups = watch('rag_groups')
  const watchedToolsEnabled = watch('tools_enabled')
  const watchedRagEnabled = watch('rag_enabled')
  const watchedTemperature = watch('temperature')
  const watchedMaxTokens = watch('max_tokens')
  const watchedAllowedModels = watch('allowed_models')

  useEffect(() => {
    agentApi.getRagKeys().then(setRagKeys).catch((e) => logger.error('Failed to load rag keys', e))
    agentApi.getRagGroups().then(setRagGroups).catch((e) => logger.error('Failed to load rag groups', e))
    getChatModels().then(setChatModels).catch((e) => logger.error('Failed to load chat models', e))
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // chatModels 로드 완료 시: initial 값을 기준으로 model/allowed_models를 ID로 동기화
  useEffect(() => {
    if (chatModels.length === 0) return

    // model: name → ID (Select value 동기화)
    const savedModel = initial?.model ?? getValues('model')
    if (savedModel && !/^\d+$/.test(savedModel)) {
      const match = chatModels.find((m) => m.name === savedModel)
      if (match) setValue('model', String(match.id))
    }

    // allowed_models: 항상 setValue로 명시 설정 (name→ID 변환 + watch 구독 갱신)
    const savedAllowed = initial?.allowed_models ?? getValues('allowed_models') ?? []
    const converted = savedAllowed.map((v) => {
      if (/^\d+$/.test(v)) return v
      const match = chatModels.find((m) => m.name === v)
      return match ? String(match.id) : v
    })
    setValue('allowed_models', [...new Set(converted)])
  }, [chatModels]) // eslint-disable-line react-hooks/exhaustive-deps

  // allowed_models: resource ID(String)로 저장 → 리소스별 고유 선택
  const toggleAllowedModel = (resourceId: string) => {
    const cur = watchedAllowedModels ?? []
    setValue('allowed_models', cur.includes(resourceId) ? cur.filter((v) => v !== resourceId) : [...cur, resourceId])
  }

  const toggleRagKey = (key: string) => {
    const cur = watchedRagKeys ?? []
    setValue('rag_keys', cur.includes(key) ? cur.filter((k) => k !== key) : [...cur, key])
  }

  const toggleRagGroup = (group: string) => {
    const cur = watchedRagGroups ?? []
    setValue('rag_groups', cur.includes(group) ? cur.filter((g) => g !== group) : [...cur, group])
  }

  const toggleTool = (toolId: string) => {
    const cur = watchedToolsEnabled ?? []
    setValue('tools_enabled', cur.includes(toolId) ? cur.filter((t) => t !== toolId) : [...cur, toolId])
  }

  const totalSelected = (watchedRagKeys?.length ?? 0) + (watchedRagGroups?.length ?? 0)

  const handleFormSubmit = async (data: AgentFormData) => {
    // model: ID → name 변환 후 백엔드 전달
    const modelResource = chatModels.find((m) => String(m.id) === data.model)
    await onSubmit(modelResource ? { ...data, model: modelResource.name } : data)
  }

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)}>
      <Tabs defaultValue="basic" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="basic">기본 정보</TabsTrigger>
          <TabsTrigger value="prompt">프롬프트</TabsTrigger>
          <TabsTrigger value="rag">
            RAG 리소스
            {totalSelected > 0 && (
              <Badge variant="secondary" className="ml-1.5 text-xs px-1.5 py-0">{totalSelected}</Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="advanced">고급 설정</TabsTrigger>
        </TabsList>

        {/* ── 기본 정보 ── */}
        <TabsContent value="basic" className="space-y-4 pt-4">
          <div className="space-y-2">
            <Label htmlFor="name">에이전트 이름 *</Label>
            <Input id="name" placeholder="예: 고객 지원 봇" {...register('name')} />
            {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">설명</Label>
            <Textarea id="description" placeholder="이 에이전트의 역할을 간략히 설명하세요" rows={2} {...register('description')} />
          </div>

          <div className="space-y-2">
            <Label htmlFor="welcome_message">환영 메시지</Label>
            <Input id="welcome_message" placeholder="안녕하세요! 무엇을 도와드릴까요?" {...register('welcome_message')} />
          </div>

          {/* 기본 모델: ID를 value로 사용 → name 중복 문제 없음 */}
          <div className="space-y-2">
            <Label>기본 모델</Label>
            <p className="text-xs text-muted-foreground">채팅 시작 시 기본으로 사용할 모델</p>
            <Select value={watch('model')} onValueChange={(v) => setValue('model', v)}>
              <SelectTrigger><SelectValue placeholder="모델 선택" /></SelectTrigger>
              <SelectContent>
                {chatModels.length === 0 ? (
                  <SelectItem value="__none__" disabled>
                    모델 없음 (LLM 리소스를 먼저 등록하세요)
                  </SelectItem>
                ) : (
                  chatModels.map((m) => (
                    <SelectItem key={String(m.id)} value={String(m.id)}>
                      {m.name}{m.model_name ? ` (${m.model_name})` : ''}
                    </SelectItem>
                  ))
                )}
              </SelectContent>
            </Select>
          </div>

          {/* 선택 가능한 모델: resource ID 기준으로 체크 → 리소스별 독립 선택 */}
          <div className="space-y-2">
            <Label>선택 가능한 모델</Label>
            <p className="text-xs text-muted-foreground">채팅 중 사용자가 전환할 수 있는 모델 목록</p>
            {chatModels.length === 0 ? (
              <p className="text-sm text-muted-foreground border border-dashed rounded-md p-3 text-center">
                LLM 리소스에 등록된 챗 모델이 없습니다
              </p>
            ) : (
              <div className="space-y-1 border rounded-md p-1.5 max-h-40 overflow-y-auto">
                {chatModels.map((m) => {
                  const selected = watchedAllowedModels?.includes(String(m.id))
                  return (
                    <button
                      key={String(m.id)}
                      type="button"
                      onClick={() => toggleAllowedModel(String(m.id))}
                      className={`w-full flex items-center gap-2 p-2 rounded-md text-left text-sm transition-colors ${
                        selected ? 'bg-primary/10 border border-primary/30' : 'hover:bg-muted'
                      }`}
                    >
                      <div className={`w-4 h-4 rounded border flex-shrink-0 flex items-center justify-center ${selected ? 'bg-primary border-primary' : 'border-muted-foreground'}`}>
                        {selected && <span className="text-primary-foreground text-xs">✓</span>}
                      </div>
                      <span className="font-medium">{m.name}</span>
                      {m.model_name && <span className="text-xs text-muted-foreground">({m.model_name})</span>}
                    </button>
                  )
                })}
              </div>
            )}
          </div>

          <div className="flex items-center justify-between rounded-lg border p-3">
            <div>
              <p className="text-sm font-medium">게시</p>
              <p className="text-xs text-muted-foreground">활성화 시 채팅 인터페이스에서 사용 가능</p>
            </div>
            <Switch checked={watch('is_published')} onCheckedChange={(v) => setValue('is_published', v)} />
          </div>
        </TabsContent>

        {/* ── 프롬프트 ── */}
        <TabsContent value="prompt" className="space-y-4 pt-4">
          <div className="space-y-2">
            <Label htmlFor="system_prompt">시스템 프롬프트</Label>
            <p className="text-xs text-muted-foreground">에이전트의 역할, 말투, 제약 사항 등을 지정하세요.</p>
            <Textarea
              id="system_prompt"
              placeholder="당신은 친절한 고객 지원 전문가입니다. 항상 공손하게 답변하고, 모르는 내용은 모른다고 말하세요."
              rows={12}
              className="font-mono text-sm"
              {...register('system_prompt')}
            />
          </div>
        </TabsContent>

        {/* ── RAG 리소스 ── */}
        <TabsContent value="rag" className="space-y-4 pt-4">
          <div className="flex items-center justify-between rounded-lg border p-3">
            <div>
              <p className="text-sm font-medium">RAG 검색 활성화</p>
              <p className="text-xs text-muted-foreground">선택한 문서에서 관련 내용을 자동으로 검색하여 답변에 활용</p>
            </div>
            <Switch checked={watchedRagEnabled} onCheckedChange={(v) => setValue('rag_enabled', v)} />
          </div>

          {watchedRagEnabled && (
            <>
              <div className="space-y-1.5">
                <Label>청크 수 (키/그룹당): {watch('rag_search_k')}</Label>
                <input
                  type="range" min={1} max={20} step={1}
                  value={watch('rag_search_k')}
                  onChange={(e) => setValue('rag_search_k', Number(e.target.value))}
                  className="w-full accent-primary"
                />
              </div>

              {totalSelected > 0 && (
                <div className="flex flex-wrap gap-1 p-2 bg-muted/40 rounded-md border">
                  {watchedRagKeys?.map((key) => (
                    <Badge key={`key-${key}`} variant="secondary" className="gap-1 text-xs">
                      <FileText className="h-3 w-3" />{key}
                      <button type="button" onClick={() => toggleRagKey(key)}>
                        <X className="h-3 w-3" />
                      </button>
                    </Badge>
                  ))}
                  {watchedRagGroups?.map((group) => (
                    <Badge key={`grp-${group}`} variant="default" className="gap-1 text-xs">
                      <FolderOpen className="h-3 w-3" />{group}
                      <button type="button" onClick={() => toggleRagGroup(group)}>
                        <X className="h-3 w-3" />
                      </button>
                    </Badge>
                  ))}
                </div>
              )}

              <Tabs defaultValue="keys" className="w-full">
                <TabsList className="w-full grid grid-cols-2">
                  <TabsTrigger value="keys" className="text-xs">
                    <FileText className="h-3.5 w-3.5 mr-1.5" />
                    개별 키
                    {(watchedRagKeys?.length ?? 0) > 0 && (
                      <Badge variant="secondary" className="ml-1 px-1 py-0 text-xs">{watchedRagKeys.length}</Badge>
                    )}
                  </TabsTrigger>
                  <TabsTrigger value="groups" className="text-xs">
                    <FolderOpen className="h-3.5 w-3.5 mr-1.5" />
                    그룹
                    {(watchedRagGroups?.length ?? 0) > 0 && (
                      <Badge variant="secondary" className="ml-1 px-1 py-0 text-xs">{watchedRagGroups.length}</Badge>
                    )}
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="keys" className="mt-2">
                  {ragKeys.length === 0 ? (
                    <p className="text-sm text-muted-foreground border border-dashed rounded-md p-4 text-center">
                      RAG 문서가 없습니다. RAG Documents 페이지에서 먼저 업로드하세요.
                    </p>
                  ) : (
                    <div className="space-y-1 max-h-56 overflow-y-auto border rounded-md p-1.5">
                      {ragKeys.map((info) => {
                        const selected = watchedRagKeys?.includes(info.rag_key)
                        return (
                          <button
                            key={info.rag_key}
                            type="button"
                            onClick={() => toggleRagKey(info.rag_key)}
                            className={`w-full flex items-center gap-3 p-2 rounded-md text-left transition-colors ${
                              selected ? 'bg-primary/10 border border-primary/30' : 'hover:bg-muted'
                            }`}
                          >
                            <div className="p-1.5 bg-primary/10 rounded flex-shrink-0">
                              <FileText className="h-3.5 w-3.5 text-primary" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium truncate">{info.rag_key}</p>
                              <p className="text-xs text-muted-foreground">
                                그룹: {info.rag_group} · {info.doc_count}개 문서
                              </p>
                            </div>
                            {selected && <Badge variant="default" className="text-xs flex-shrink-0">선택됨</Badge>}
                          </button>
                        )
                      })}
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="groups" className="mt-2">
                  <p className="text-xs text-muted-foreground mb-2">
                    그룹을 선택하면 해당 그룹의 모든 키를 한 번에 검색합니다.
                  </p>
                  {ragGroups.length === 0 ? (
                    <p className="text-sm text-muted-foreground border border-dashed rounded-md p-4 text-center">
                      그룹이 없습니다. 문서를 업로드할 때 rag_group을 지정하면 그룹이 생성됩니다.
                    </p>
                  ) : (
                    <div className="space-y-1 max-h-56 overflow-y-auto border rounded-md p-1.5">
                      {ragGroups.map((info) => {
                        const selected = watchedRagGroups?.includes(info.rag_group)
                        return (
                          <button
                            key={info.rag_group}
                            type="button"
                            onClick={() => toggleRagGroup(info.rag_group)}
                            className={`w-full flex items-center gap-3 p-2 rounded-md text-left transition-colors ${
                              selected ? 'bg-primary/10 border border-primary/30' : 'hover:bg-muted'
                            }`}
                          >
                            <div className="p-1.5 bg-amber-100 dark:bg-amber-900/30 rounded flex-shrink-0">
                              <FolderOpen className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium truncate">{info.rag_group}</p>
                              <p className="text-xs text-muted-foreground">
                                {info.key_count}개 키 · {info.doc_count}개 문서
                              </p>
                            </div>
                            {selected && <Badge variant="default" className="text-xs flex-shrink-0">선택됨</Badge>}
                          </button>
                        )
                      })}
                    </div>
                  )}
                </TabsContent>
              </Tabs>
            </>
          )}
        </TabsContent>

        {/* ── 고급 설정 ── */}
        <TabsContent value="advanced" className="space-y-4 pt-4">
          <div className="space-y-2">
            <Label>Temperature: {watchedTemperature?.toFixed(1)}</Label>
            <p className="text-xs text-muted-foreground">높을수록 창의적, 낮을수록 일관성 있는 답변</p>
            <input
              type="range" min={0} max={2} step={0.1}
              value={watchedTemperature ?? 0.7}
              onChange={(e) => setValue('temperature', Number(e.target.value))}
              className="w-full accent-primary"
            />
          </div>

          <div className="space-y-2">
            <Label>최대 토큰: {watchedMaxTokens}</Label>
            <input
              type="range" min={256} max={16000} step={256}
              value={watchedMaxTokens ?? 2000}
              onChange={(e) => setValue('max_tokens', Number(e.target.value))}
              className="w-full accent-primary"
            />
          </div>

          <div className="space-y-2">
            <Label>도구</Label>
            {AVAILABLE_TOOLS.map(({ id, label, icon: Icon }) => (
              <div key={id} className="flex items-center justify-between rounded-lg border p-3">
                <div className="flex items-center gap-2">
                  <Icon className="h-4 w-4 text-muted-foreground" />
                  <p className="text-sm font-medium">{label}</p>
                </div>
                <Switch
                  checked={watchedToolsEnabled?.includes(id) ?? false}
                  onCheckedChange={() => toggleTool(id)}
                />
              </div>
            ))}
          </div>
        </TabsContent>
      </Tabs>

      <div className="pt-6">
        <Button type="submit" disabled={isLoading} className="w-full">
          {isLoading ? '저장 중...' : initial ? '수정 저장' : '에이전트 생성'}
        </Button>
      </div>
    </form>
  )
}
