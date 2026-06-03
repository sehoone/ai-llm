'use client'

import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import * as api from '@/api/sample'
import { Section, ErrorMsg } from '../section'

export function TabDeepThinking() {
  const [message, setMessage] = useState('')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [sections, setSections] = useState<string[]>([])
  const [content, setContent] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const reset = () => { setContent(''); setSections([]); setSessionId(null) }

  const handleSync = async () => {
    if (!message.trim()) return
    setLoading(true); setError(null); reset()
    try {
      const res = await api.sendDeepThinking({ message, session_id: sessionId ?? undefined })
      setSessionId(res.session_id)
      setContent(res.response)
      setSections(res.sections)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '오류가 발생했습니다')
    } finally {
      setLoading(false)
    }
  }

  const handleStream = async () => {
    if (!message.trim()) return
    setLoading(true); setError(null); reset()
    let buf = ''
    try {
      await api.streamDeepThinking(
        { message, session_id: sessionId ?? undefined },
        {
          onToken: (t) => { buf += t; setContent(buf) },
          onSessionId: (sid) => setSessionId(sid),
          onEvent: (event, data) => {
            if (event === 'section') {
              try { setSections((prev) => [...prev, JSON.parse(data).section]) } catch { /* noop */ }
            }
          },
        },
      )
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '오류가 발생했습니다')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className='space-y-4'>
      <Section title='딥씽킹 채팅' endpoint='/api/v1/sample/deep-thinking/' method='POST'>
        <p className='mb-3 text-xs text-muted-foreground'>
          think → chat → verify 품질 루프. "비교", "분석", "설계" 등 복잡한 질문 입력 시 효과적입니다.
        </p>
        <div className='flex gap-2'>
          <Input
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder='마이크로서비스와 모놀리식의 장단점을 비교 분석해주세요'
            disabled={loading}
            className='flex-1'
          />
          <Button onClick={handleSync} disabled={loading || !message.trim()} size='sm' variant='outline'>동기</Button>
          <Button onClick={handleStream} disabled={loading || !message.trim()} size='sm'>스트림</Button>
        </div>

        {sessionId && (
          <p className='mt-1 text-xs text-muted-foreground'>session: {sessionId.slice(0, 8)}…</p>
        )}

        {sections.length > 0 && (
          <div className='mt-2 flex gap-1'>
            {sections.map((s, i) => (
              <Badge key={i} variant='secondary' className='text-xs capitalize'>{s}</Badge>
            ))}
          </div>
        )}

        {content && (
          <div className='relative mt-2 rounded-md bg-muted p-3 text-sm whitespace-pre-wrap'>
            {content}
            {loading && <span className='ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-current align-middle' />}
          </div>
        )}
        <ErrorMsg error={error} />
      </Section>
    </div>
  )
}
