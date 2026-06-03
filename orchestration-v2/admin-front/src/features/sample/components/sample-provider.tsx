'use client'

import React, { useState, useRef } from 'react'
import { logger } from '@/lib/logger'
import * as sampleApi from '@/api/sample'
import type { ChatMessage } from '../data/schema'

type ChatContextType = {
  messages: ChatMessage[]
  sessionId: string | null
  isLoading: boolean
  isStreaming: boolean
  sendMessage: (text: string) => Promise<void>
  streamMessage: (text: string) => Promise<void>
  resetSession: () => void
}

const ChatContext = React.createContext<ChatContextType | null>(null)

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)
  const streamBufferRef = useRef('')

  const sendMessage = async (text: string) => {
    setMessages((prev) => [...prev, { role: 'user', content: text }])
    setIsLoading(true)
    try {
      const res = await sampleApi.sendChat({ message: text, session_id: sessionId ?? undefined })
      if (res.session_id) setSessionId(res.session_id)
      setMessages((prev) => [...prev, { role: 'assistant', content: res.response }])
    } catch (error) {
      logger.error('Failed to send chat', error)
      throw error
    } finally {
      setIsLoading(false)
    }
  }

  const streamMessage = async (text: string) => {
    streamBufferRef.current = ''
    setMessages((prev) => [...prev, { role: 'user', content: text }, { role: 'assistant', content: '' }])
    setIsStreaming(true)
    try {
      await sampleApi.streamChat(
        { message: text, session_id: sessionId ?? undefined },
        {
          onToken: (token) => {
            streamBufferRef.current += token
            const content = streamBufferRef.current
            setMessages((prev) => {
              const updated = [...prev]
              updated[updated.length - 1] = { role: 'assistant', content }
              return updated
            })
          },
          onSessionId: (sid) => setSessionId(sid),
        },
      )
    } catch (error) {
      logger.error('Failed to stream chat', error)
      throw error
    } finally {
      setIsStreaming(false)
    }
  }

  const resetSession = () => {
    setMessages([])
    setSessionId(null)
  }

  return (
    <ChatContext.Provider value={{ messages, sessionId, isLoading, isStreaming, sendMessage, streamMessage, resetSession }}>
      {children}
    </ChatContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export const useChat = () => {
  const context = React.useContext(ChatContext)
  if (!context) throw new Error('useChat has to be used within <ChatProvider>')
  return context
}
