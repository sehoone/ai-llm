/* eslint-disable @typescript-eslint/no-explicit-any */
'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { chatService } from '@/api/chat'
import { type ChatHistoryResponse } from '@/types/chat-api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ArrowLeft, Calendar, User, MessageCircle } from 'lucide-react'
import { format } from 'date-fns'
import ReactMarkdown from 'react-markdown'
import { logger } from '@/lib/logger'

export default function ChatHistoryDetailPage() {
  const params = useParams()
  const router = useRouter()
  const [data, setData] = useState<ChatHistoryResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadData = async () => {
      if (!params || !params.id) return
      try {
        setLoading(true)
        const id = Array.isArray(params.id) ? params.id[0] : params.id
        const result = await chatService.getChatHistoryDetail(Number(id))
        setData(result)
      } catch (err: any) {
        logger.error(err)
        setError(err.message || 'Failed to load details')
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [params])

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-destructive">
        <h2 className="text-lg font-semibold">Error Loading Detail</h2>
        <p>{error}</p>
        <Button variant="outline" onClick={() => router.back()} className="mt-4">
          Go Back
        </Button>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="flex flex-col items-center justify-center p-8">
        <h2 className="text-lg font-semibold">Not Found</h2>
        <Button variant="outline" onClick={() => router.back()} className="mt-4">
          Go Back
        </Button>
      </div>
    )
  }

  return (
    <div className="h-full flex-1 flex-col space-y-8 p-8 md:flex">
      <div className="flex items-center justify-between space-y-2">
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <h2 className="text-2xl font-bold tracking-tight">Conversation Detail</h2>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        <div className="col-span-4 lg:col-span-5 space-y-4">
          {/* Question Card */}
          <Card>
            <CardHeader className="!pb-3 border-b">
              <CardTitle className="flex items-center gap-2 text-base font-medium">
                <User className="h-4 w-4" />
                질문
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-2">
              <div className="whitespace-pre-wrap text-sm leading-relaxed">
                {data.question}
              </div>
            </CardContent>
          </Card>

          {/* Answer Card */}
          <Card className="border-primary/20">
            <CardHeader className="!pb-3 border-b border-primary/10">
              <CardTitle className="flex items-center gap-2 text-base font-medium text-primary">
                <MessageCircle className="h-4 w-4" />
                답변
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-2">
              <div className="prose prose-sm dark:prose-invert max-w-none">
                <ReactMarkdown>
                  {data.answer}
                </ReactMarkdown>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="col-span-4 lg:col-span-2 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Metadata</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-col space-y-1">
                <span className="text-xs font-medium text-muted-foreground">Date</span>
                <span className="flex items-center gap-2 text-sm">
                  <Calendar className="h-3 w-3 text-muted-foreground" />
                  {format(new Date(data.created_at), 'yyyy-MM-dd HH:mm:ss')}
                </span>
              </div>
              
              <div className="flex flex-col space-y-1">
                <span className="text-xs font-medium text-muted-foreground">Session</span>
                <span className="text-sm font-medium">{data.session_name || 'No Name'}</span>
                <span className="text-xs font-mono text-muted-foreground break-all">
                  {data.session_id}
                </span>
              </div>

              <div className="flex flex-col space-y-1">
                <span className="text-xs font-medium text-muted-foreground">User Email</span>
                <span className="text-sm break-all">{data.user_email}</span>
              </div>

              <div className="flex flex-col space-y-1">
                <span className="text-xs font-medium text-muted-foreground">Message ID</span>
                <span className="text-xs font-mono text-muted-foreground">{data.id}</span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
