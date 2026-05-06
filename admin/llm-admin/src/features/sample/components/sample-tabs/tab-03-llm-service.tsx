'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import * as api from '@/api/sample'
import { Section, JsonResult, ErrorMsg } from '../section'

function useApiCall<T>() {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const run = async (fn: () => Promise<T>) => {
    setLoading(true); setError(null)
    try { setData(await fn()) }
    catch (e: unknown) { setError(e instanceof Error ? e.message : '오류') }
    finally { setLoading(false) }
  }

  return { data, loading, error, run }
}

export function TabLlmService() {
  const info = useApiCall<unknown>()
  const call = useApiCall<api.LLMCallResponse>()
  const cb = useApiCall<unknown>()
  const [message, setMessage] = useState('')

  return (
    <div className='space-y-4'>
      <Section title='LLM 서비스 현황' endpoint='/api/v1/sample/llm/info'>
        <Button size='sm' onClick={() => info.run(() => api.getLlmInfo())} disabled={info.loading}>
          {info.loading ? '조회 중…' : '조회'}
        </Button>
        <JsonResult data={info.data} />
        <ErrorMsg error={info.error} />
      </Section>

      <Section title='LLM 직접 호출' endpoint='/api/v1/sample/llm/call' method='POST'>
        <p className='mb-2 text-xs text-muted-foreground'>
          DB 리소스 → Priority + Weighted Random → Circuit Breaker → LLMRegistry fallback 순으로 선택됩니다.
        </p>
        <div className='flex gap-2'>
          <Input
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder='안녕하세요!'
            disabled={call.loading}
            className='flex-1'
          />
          <Button
            size='sm'
            onClick={() => call.run(() => api.callLlm({ message }))}
            disabled={call.loading || !message.trim()}
          >
            {call.loading ? '호출 중…' : '호출'}
          </Button>
        </div>
        {call.data && (
          <div className='mt-2 space-y-1'>
            <p className='rounded-md bg-muted p-3 text-sm'>{call.data.response}</p>
            {call.data.model_used && (
              <p className='text-xs text-muted-foreground'>model: {call.data.model_used}</p>
            )}
          </div>
        )}
        <ErrorMsg error={call.error} />
      </Section>

      <Section title='Circuit Breaker 상태' endpoint='/api/v1/sample/llm/circuit-breakers'>
        <p className='mb-2 text-xs text-muted-foreground'>
          연속 3회 실패 시 OPEN (30초 차단) → HALF_OPEN → CLOSED 순으로 복구됩니다.
        </p>
        <Button size='sm' onClick={() => cb.run(() => api.getCircuitBreakers())} disabled={cb.loading}>
          {cb.loading ? '조회 중…' : '조회'}
        </Button>
        <JsonResult data={cb.data} />
        <ErrorMsg error={cb.error} />
      </Section>
    </div>
  )
}
