'use client'

import { useState } from 'react'
import { toast } from 'sonner'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  Search, Loader2, ExternalLink,
  ChevronDown, ChevronUp, RotateCcw, Bot, FileText,
} from 'lucide-react'
import { aiOverviewApi, type AiOverviewSource } from '@/api/ai-overview'
import { DEFAULT_LLM_MODEL, type LlmModel, LLM_MODELS } from '@/config/models'
import { logger } from '@/lib/logger'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { markdownComponents } from '@/components/markdown-components'

const DEFAULT_SYSTEM_PROMPT = `당신은 사내 AI Overview 어시스턴트입니다.
사용자 질문에 대해 검색된 사내 문서를 기반으로 정확하고 유용한 답변을 제공하세요.

규칙:
- 검색된 문서가 있으면 해당 내용 기반으로 답변하고 출처를 [문서명]으로 표시하세요
- 문서가 없거나 관련 내용이 없으면 일반 지식으로 답변하되 "사내 데이터 없음"을 명시하세요
- 답변은 간결하고 구조화되게 작성하세요 (마크다운 사용)`

// ── 출처 카드 ─────────────────────────────────────────────────────────────────
function SourceCard({ src }: { src: AiOverviewSource }) {
  const pct = Math.round(src.score * 100)
  return (
    <div className='flex flex-col gap-2 rounded-lg border bg-card p-3 hover:bg-muted/40 transition-colors'>
      <div className='flex items-start gap-2'>
        <FileText className='h-4 w-4 mt-0.5 shrink-0 text-muted-foreground' />
        <p className='text-sm font-medium line-clamp-2 flex-1 leading-tight'>{src.title}</p>
      </div>
      <div className='flex items-center gap-2'>
        <div className='flex-1 h-1.5 rounded-full bg-muted overflow-hidden'>
          <div
            className='h-full rounded-full bg-primary/60'
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className='text-xs text-muted-foreground tabular-nums w-8 text-right'>{pct}%</span>
        {src.source_url && (
          <a href={src.source_url} target='_blank' rel='noreferrer'
            className='text-muted-foreground hover:text-foreground transition-colors'>
            <ExternalLink className='h-3.5 w-3.5' />
          </a>
        )}
      </div>
    </div>
  )
}

// ── 바운싱 로딩 점 ─────────────────────────────────────────────────────────────
function BouncingDots() {
  return (
    <div className='flex items-center gap-1 py-1'>
      <span className='h-2 w-2 animate-bounce rounded-full bg-foreground/40 [animation-delay:-0.3s]' />
      <span className='h-2 w-2 animate-bounce rounded-full bg-foreground/40 [animation-delay:-0.15s]' />
      <span className='h-2 w-2 animate-bounce rounded-full bg-foreground/40' />
    </div>
  )
}

// ── 메인 ──────────────────────────────────────────────────────────────────────
export default function AiOverview() {
  const [query, setQuery] = useState('')
  const [model, setModel] = useState<LlmModel>(DEFAULT_LLM_MODEL)
  const [systemPrompt, setSystemPrompt] = useState('')
  const [showConfig, setShowConfig] = useState(false)

  const [loading, setLoading] = useState(false)
  const [streaming, setStreaming] = useState(false)
  const [hasStarted, setHasStarted] = useState(false)
  const [keywords, setKeywords] = useState<string[]>([])
  const [sources, setSources] = useState<AiOverviewSource[]>([])
  const [answer, setAnswer] = useState('')

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return

    setLoading(true)
    setStreaming(false)
    setHasStarted(true)
    setKeywords([])
    setSources([])
    setAnswer('')

    try {
      await aiOverviewApi.searchStream(
        query.trim(),
        model,
        (event) => {
          if (event.type === 'keywords') {
            setKeywords(event.data as string[])
          } else if (event.type === 'sources') {
            setSources(event.data as AiOverviewSource[])
            setLoading(false)
            setStreaming(true)
          } else if (event.type === 'chunk') {
            setAnswer((prev) => prev + (event.data as string))
          } else if (event.type === 'error') {
            toast.error(event.data as string)
          }
        },
        (error) => { logger.error('AI Overview stream error', error) },
        systemPrompt.trim() || undefined,
      )
    } catch (error) {
      logger.error(error)
      toast.error('검색 중 오류가 발생했습니다')
    } finally {
      setLoading(false)
      setStreaming(false)
    }
  }

  const isCustomPrompt = systemPrompt.trim().length > 0

  return (
    <div className='flex flex-col gap-4 p-4 md:p-8 max-w-4xl mx-auto w-full'>
      <div>
        <h2 className='text-3xl font-bold tracking-tight'>AI Overview</h2>
        <p className='text-muted-foreground mt-1'>사내 데이터 기반 AI 답변 검색</p>
      </div>

      {/* ── 검색 폼 ── */}
      <form onSubmit={handleSearch} className='flex flex-col gap-2'>
        <div className='flex gap-2'>
          <div className='relative flex-1'>
            <Search className='absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground' />
            <Input
              placeholder='무엇이든 물어보세요...'
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className='pl-9 h-11'
              disabled={loading || streaming}
            />
          </div>
          <Select value={model} onValueChange={(v) => setModel(v as LlmModel)}>
            <SelectTrigger className='w-[150px] h-11'>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {LLM_MODELS.map((m) => (
                <SelectItem key={m.id} value={m.id}>{m.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button type='submit' disabled={loading || streaming || !query.trim()} className='h-11 px-6'>
            {loading ? <Loader2 className='h-4 w-4 animate-spin' /> : '검색'}
          </Button>
        </div>

        {/* 시스템 프롬프트 토글 */}
        <div>
          <button
            type='button'
            onClick={() => setShowConfig((v) => !v)}
            className='flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors'
          >
            {showConfig ? <ChevronUp className='h-3.5 w-3.5' /> : <ChevronDown className='h-3.5 w-3.5' />}
            시스템 프롬프트 설정
            {isCustomPrompt && (
              <Badge variant='secondary' className='text-xs px-1.5 py-0 ml-1'>커스텀 적용 중</Badge>
            )}
          </button>
          {showConfig && (
            <div className='mt-2 flex flex-col gap-1.5 rounded-lg border bg-muted/30 p-3'>
              <div className='flex items-center justify-between'>
                <Label className='text-xs font-medium'>시스템 프롬프트</Label>
                {isCustomPrompt && (
                  <button type='button' onClick={() => setSystemPrompt('')}
                    className='flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground'>
                    <RotateCcw className='h-3 w-3' />기본값으로 초기화
                  </button>
                )}
              </div>
              <Textarea
                placeholder={DEFAULT_SYSTEM_PROMPT}
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                className='min-h-[120px] resize-y text-sm font-mono'
                disabled={loading || streaming}
              />
              <p className='text-xs text-muted-foreground'>비워두면 기본 프롬프트가 사용됩니다.</p>
            </div>
          )}
        </div>
      </form>

      {/* ── 결과 영역 ── */}
      {hasStarted && (
        <div className='flex flex-col gap-4'>

          {/* Answer Card */}
          <div className={cn(
            'rounded-xl border bg-card shadow-sm overflow-hidden transition-all',
            streaming && 'border-l-4 border-l-primary',
          )}>
            {/* 카드 헤더 */}
            <div className='flex items-center justify-between gap-3 px-4 py-3 border-b bg-muted/20'>
              <div className='flex items-center gap-2.5'>
                <div className='flex h-8 w-8 shrink-0 items-center justify-center rounded-md border bg-background shadow-sm'>
                  <Bot className='h-4 w-4' />
                </div>
                <div className='flex flex-col gap-0.5'>
                  <span className='text-sm font-semibold'>AI Overview</span>
                  {/* 검색 키워드 */}
                  {keywords.length > 0 && (
                    <div className='flex items-center gap-1 flex-wrap'>
                      <span className='text-xs text-muted-foreground'>키워드:</span>
                      {keywords.map((kw) => (
                        <Badge key={kw} variant='secondary' className='text-xs px-1.5 py-0 h-4'>{kw}</Badge>
                      ))}
                    </div>
                  )}
                </div>
              </div>
              <div className='flex items-center gap-1.5 shrink-0'>
                {isCustomPrompt && (
                  <Badge variant='outline' className='text-xs font-normal'>커스텀 프롬프트</Badge>
                )}
                <Badge variant='secondary' className='text-xs font-normal'>{model}</Badge>
              </div>
            </div>

            {/* 카드 본문 */}
            <div className='px-5 py-4'>
              {/* 로딩: 바운싱 점 */}
              {loading && <BouncingDots />}

              {/* 스트리밍 시작 전 대기 */}
              {!loading && streaming && !answer && <BouncingDots />}

              {/* 답변 본문 */}
              {answer && (
                <div className='prose prose-sm dark:prose-invert max-w-none animate-in fade-in duration-500
                  prose-headings:font-semibold prose-headings:tracking-tight
                  prose-h1:text-xl prose-h2:text-lg prose-h3:text-base
                  prose-code:bg-muted prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm prose-code:font-mono
                  prose-pre:bg-muted prose-pre:border prose-pre:rounded-lg
                  prose-blockquote:border-l-primary prose-blockquote:text-muted-foreground
                  prose-li:marker:text-muted-foreground'>
                  <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                    {answer}
                  </ReactMarkdown>
                  {streaming && (
                    <span className='inline-block w-0.5 h-4 bg-foreground/60 animate-pulse ml-0.5 align-middle' />
                  )}
                </div>
              )}
            </div>
          </div>

          {/* 출처 문서 카드 그리드 */}
          {sources.length > 0 && (
            <div className='flex flex-col gap-2'>
              <p className='text-sm font-medium text-muted-foreground'>
                출처 문서 <span className='text-xs'>({sources.length})</span>
              </p>
              <div className='grid grid-cols-2 gap-2 sm:grid-cols-3'>
                {sources.map((src) => (
                  <SourceCard key={src.id} src={src} />
                ))}
              </div>
            </div>
          )}

          {/* 사내 데이터 없음 안내 */}
          {!loading && !streaming && sources.length === 0 && answer && (
            <p className='text-xs text-muted-foreground flex items-center gap-1.5'>
              <Search className='h-3 w-3' />
              사내 데이터 기반 출처 없음 — 일반 지식으로 답변했습니다
            </p>
          )}
        </div>
      )}
    </div>
  )
}
