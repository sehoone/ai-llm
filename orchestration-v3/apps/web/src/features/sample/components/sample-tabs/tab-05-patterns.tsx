'use client'

import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import * as api from '@/api/sample'
import { Section, JsonResult } from '../section'

export function TabPatterns() {
  const [streamMsg, setStreamMsg] = useState('')
  const [streamOutput, setStreamOutput] = useState('')
  const [streamSections, setStreamSections] = useState<{ section: string; label: string }[]>([])
  const [streamLoading, setStreamLoading] = useState(false)
  const [streamMode, setStreamMode] = useState<'basic' | 'sectioned'>('basic')

  const [rateLimitResult, setRateLimitResult] = useState<unknown>(null)
  const [rateLimitError, setRateLimitError] = useState<string | null>(null)
  const [rateLimitCount, setRateLimitCount] = useState(0)

  const [middlewareResult, setMiddlewareResult] = useState<unknown>(null)

  const handleStream = async () => {
    if (!streamMsg.trim()) return
    setStreamLoading(true); setStreamOutput(''); setStreamSections([])
    let buf = ''
    const fn = streamMode === 'basic' ? api.streamBasicPattern : api.streamSectionedPattern
    try {
      await fn(
        { message: streamMsg },
        {
          onToken: (t) => { buf += t; setStreamOutput(buf) },
          onEvent: (event, data) => {
            if (event === 'section') {
              try { setStreamSections((prev) => [...prev, JSON.parse(data)]) } catch { /* noop */ }
            }
          },
        },
      )
    } finally {
      setStreamLoading(false)
    }
  }

  const handleRateLimit = async () => {
    setRateLimitError(null)
    try {
      const res = await api.getRateLimitTest()
      setRateLimitResult(res)
      setRateLimitCount((n) => n + 1)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '오류'
      setRateLimitError(msg)
      setRateLimitCount((n) => n + 1)
    }
  }

  return (
    <div className='space-y-4'>
      <Section title='SSE 스트리밍 패턴' endpoint='/api/v1/sample/patterns/stream/' method='POST'>
        <p className='mb-2 text-xs text-muted-foreground'>
          basic: 단순 토큰 스트림 | sectioned: 딥씽킹 섹션 이벤트 포함
        </p>
        <div className='mb-2 flex gap-2'>
          {(['basic', 'sectioned'] as const).map((mode) => (
            <Button
              key={mode}
              size='sm'
              variant={streamMode === mode ? 'default' : 'outline'}
              onClick={() => setStreamMode(mode)}
            >
              {mode}
            </Button>
          ))}
        </div>
        <div className='flex gap-2'>
          <Input
            value={streamMsg}
            onChange={(e) => setStreamMsg(e.target.value)}
            placeholder='스트리밍 테스트 메시지...'
            disabled={streamLoading}
            className='flex-1'
          />
          <Button size='sm' onClick={handleStream} disabled={streamLoading || !streamMsg.trim()}>
            {streamLoading ? '스트리밍 중…' : '시작'}
          </Button>
        </div>
        {streamSections.length > 0 && (
          <div className='mt-2 flex gap-1'>
            {streamSections.map((s, i) => (
              <Badge key={i} variant='secondary' className='text-xs'>{s.label || s.section}</Badge>
            ))}
          </div>
        )}
        {streamOutput && (
          <div className='mt-2 rounded-md bg-muted p-3 text-sm whitespace-pre-wrap'>
            {streamOutput}
            {streamLoading && <span className='ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-current align-middle' />}
          </div>
        )}
      </Section>

      <Section title='레이트 리밋 테스트 (5/min)' endpoint='/api/v1/sample/patterns/rate-limit-test'>
        <p className='mb-2 text-xs text-muted-foreground'>
          분당 5회 제한. 6번째 요청부터 HTTP 429가 반환됩니다. (현재 {rateLimitCount}회 시도)
        </p>
        <Button size='sm' onClick={handleRateLimit}>요청 ({rateLimitCount})</Button>
        <JsonResult data={rateLimitResult} />
        {rateLimitError && (
          <p className='mt-2 text-xs text-destructive'>
            {rateLimitError} — 5회 초과 시 429 응답
          </p>
        )}
      </Section>

      <Section title='미들웨어 체인 정보' endpoint='/api/v1/sample/patterns/middleware-info'>
        <p className='mb-2 text-xs text-muted-foreground'>
          RequestID → LoggingContext → Metrics → CORS 미들웨어 순으로 실행됩니다.
        </p>
        <Button size='sm' onClick={async () => setMiddlewareResult(await api.getMiddlewareInfo())}>
          조회
        </Button>
        <JsonResult data={middlewareResult} />
      </Section>
    </div>
  )
}
