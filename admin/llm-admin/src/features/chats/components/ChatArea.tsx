'use client'

import { useEffect, useRef } from 'react'
import { Message } from '@/types/chat-api'
import { cn } from '@/lib/utils'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import ReactMarkdown from 'react-markdown'
import { Bot, User } from 'lucide-react'

interface ChatAreaProps {
  messages: Message[]
  isLoading: boolean
}

export function ChatArea({ messages, isLoading }: ChatAreaProps) {
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, isLoading])

  return (
    <div className='flex-1 overflow-y-auto p-4' ref={scrollRef}>
      <div className='flex flex-col gap-4'>
        {messages.map((message, index) => (
          <div
            key={index}
            className={cn(
              'flex w-full gap-4 p-4 rounded-lg',
              message.role === 'user' ? 'bg-muted/50' : 'bg-background'
            )}
          >
            <div className='flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-md border shadow'>
              {message.role === 'user' ? (
                <User className='h-4 w-4' />
              ) : (
                <Bot className='h-4 w-4' />
              )}
            </div>
            <div className='flex-1 space-y-2 overflow-hidden'>
              <div className='prose break-words dark:prose-invert'>
                {message.role === 'user' ? (
                  <p className="whitespace-pre-wrap">{message.content}</p>
                ) : (
                  <ReactMarkdown>{message.content}</ReactMarkdown>
                )}
              </div>
            </div>
          </div>
        ))}
        {isLoading && (
           <div className='flex w-full gap-4 p-4 rounded-lg bg-background'>
            <div className='flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-md border shadow'>
                <Bot className='h-4 w-4' />
            </div>
            <div className='flex items-center gap-1'>
              <span className='h-1.5 w-1.5 animate-bounce rounded-full bg-foreground/50 [animation-delay:-0.3s]' />
              <span className='h-1.5 w-1.5 animate-bounce rounded-full bg-foreground/50 [animation-delay:-0.15s]' />
              <span className='h-1.5 w-1.5 animate-bounce rounded-full bg-foreground/50' />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
