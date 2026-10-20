'use client'

import { useRef, useEffect, useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ChatProvider, useChat } from '../sample-provider'

function ChatContent() {
  const { messages, sessionId, isLoading, isStreaming, sendMessage, streamMessage, resetSession } = useChat()
  const [input, setInput] = useState('')
  const [useStream, setUseStream] = useState(true)
  const bottomRef = useRef<HTMLDivElement>(null)
  const isProcessing = isLoading || isStreaming

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const text = input.trim()
    if (!text || isProcessing) return
    setInput('')
    try {
      if (useStream) await streamMessage(text)
      else await sendMessage(text)
    } catch {
      // errors logged in provider
    }
  }

  return (
    <div className='flex flex-col gap-4'>
      <div className='flex items-center justify-between'>
        {sessionId ? (
          <Badge variant='outline' className='font-mono text-xs'>session: {sessionId.slice(0, 8)}…</Badge>
        ) : <span />}
        <Button variant='outline' size='sm' onClick={resetSession}>New Session</Button>
      </div>

      <div className='flex flex-col rounded-lg border'>
        <div className='h-[55vh] overflow-y-auto p-4'>
          {messages.length === 0 && (
            <p className='py-8 text-center text-sm text-muted-foreground'>메시지를 입력해 채팅을 시작하세요.</p>
          )}
          <div className='space-y-4'>
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[70%] rounded-lg px-4 py-2 text-sm ${msg.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-muted'}`}>
                  <p className='whitespace-pre-wrap break-words'>
                    {msg.content || (isStreaming && i === messages.length - 1 ? '…' : '')}
                  </p>
                  {msg.role === 'assistant' && isStreaming && i === messages.length - 1 && msg.content && (
                    <span className='ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-current align-middle' />
                  )}
                </div>
              </div>
            ))}
          </div>
          <div ref={bottomRef} />
        </div>
        <div className='border-t p-4'>
          <form onSubmit={handleSubmit} className='flex gap-2'>
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder='메시지를 입력하세요...'
              disabled={isProcessing}
              className='flex-1'
            />
            <Button
              type='button'
              variant='outline'
              size='sm'
              title={useStream ? 'SSE 스트리밍 모드' : '동기 모드'}
              onClick={() => setUseStream(!useStream)}
            >
              {useStream ? 'Stream' : 'Sync'}
            </Button>
            <Button type='submit' disabled={isProcessing || !input.trim()}>
              {isProcessing ? '전송 중…' : '전송'}
            </Button>
          </form>
        </div>
      </div>
    </div>
  )
}

export function TabBasicChat() {
  return (
    <ChatProvider>
      <ChatContent />
    </ChatProvider>
  )
}
