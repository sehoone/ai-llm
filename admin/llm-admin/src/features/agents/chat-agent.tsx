'use client'

import { useEffect, useState, Fragment } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { agentApi, type Agent, type AgentSession } from '@/api/agents'
import { getChatModels, type ChatModel } from '@/api/llm-resources'
import { type Message } from '@/types/chat-api'
import { ChatArea } from '@/features/chats/components/chat-area'
import { Header } from '@/components/layout/header'
import { Main } from '@/components/layout/main'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { ThemeSwitch } from '@/components/theme-switch'
import { ConfigDrawer } from '@/components/config-drawer'
import { ProfileDropdown } from '@/components/profile-dropdown'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { ArrowLeft, BrainCircuit, Edit, MessagesSquare, Send, Trash2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'
import { logger } from '@/lib/logger'

export function AgentChat() {
  const params = useParams()
  const router = useRouter()
  const agentId = params.agentId as string

  const [agent, setAgent] = useState<Agent | null>(null)
  const [sessions, setSessions] = useState<AgentSession[]>([])
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null)
  const [mobileSelectedSessionId, setMobileSelectedSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [isSending, setIsSending] = useState(false)
  const [isDeepThinking, setIsDeepThinking] = useState(false)
  const [selectedModel, setSelectedModel] = useState<string | null>(null)
  const [chatModels, setChatModels] = useState<ChatModel[]>([])
  const [inputMessage, setInputMessage] = useState('')
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [sessionToDelete, setSessionToDelete] = useState<string | null>(null)

  useEffect(() => {
    getChatModels().then(setChatModels).catch((e) => {
      logger.warn('Failed to load chat models', e)
    })
  }, [])

  useEffect(() => {
    if (!agentId) return
    agentApi.get(agentId).then((a) => {
      setAgent(a)
      setSelectedModel(a.allowed_models?.[0] ?? null)
    }).catch((e) => {
      logger.error('Failed to load agent', e)
      toast.error('에이전트를 불러오지 못했습니다')
      router.push('/agents')
    })
    loadSessions()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agentId])

  useEffect(() => {
    if (selectedSessionId) {
      agentApi.getMessages(agentId, selectedSessionId).then(setMessages).catch((e) => {
        logger.error('Failed to load messages', e)
      })
    } else {
      setMessages([])
    }
  }, [selectedSessionId, agentId])

  const loadSessions = async () => {
    try {
      const data = await agentApi.getSessions(agentId)
      setSessions(data)
      if (data.length > 0) {
        setSelectedSessionId(data[0].session_id)
        setMobileSelectedSessionId(data[0].session_id)
      }
    } catch (e) {
      logger.error('Failed to load sessions', e)
    }
  }

  const handleCreateSession = async () => {
    try {
      const s = await agentApi.createSession(agentId)
      setSessions((prev) => [s, ...prev])
      setSelectedSessionId(s.session_id)
      setMobileSelectedSessionId(s.session_id)
      setMessages([])
    } catch (e) {
      logger.error('Failed to create session', e)
      toast.error('세션 생성에 실패했습니다')
    }
  }

  const handleDeleteSession = async () => {
    if (!sessionToDelete) return
    try {
      await agentApi.deleteSession(agentId, sessionToDelete)
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionToDelete))
      if (selectedSessionId === sessionToDelete) {
        setSelectedSessionId(null)
        setMobileSelectedSessionId(null)
      }
      setDeleteDialogOpen(false)
      setSessionToDelete(null)
    } catch (e) {
      logger.error('Failed to delete session', e)
      toast.error('세션 삭제에 실패했습니다')
    }
  }

  const handleSendMessage = async (e?: React.FormEvent) => {
    e?.preventDefault()
    if (!inputMessage.trim() || !selectedSessionId || isSending) return

    const userMessage: Message = { role: 'user', content: inputMessage.trim() }
    setMessages((prev) => [...prev, userMessage, { role: 'assistant', content: '' }])
    setInputMessage('')
    setIsSending(true)
    let currentResponse = ''

    try {
      await agentApi.streamMessage(
        agentId,
        selectedSessionId,
        [...messages, userMessage],
        (chunk, done, title) => {
          if (title) {
            setSessions((prev) =>
              prev.map((s) => s.session_id === selectedSessionId ? { ...s, name: title } : s)
            )
          }
          currentResponse += chunk
          setMessages((prev) => {
            const next = [...prev]
            next[next.length - 1] = { ...next[next.length - 1], content: currentResponse }
            return next
          })
          if (done) setIsSending(false)
        },
        (error) => {
          logger.error('Failed to send message', error)
          toast.error('메시지 전송에 실패했습니다')
          setIsSending(false)
        },
        isDeepThinking,
        selectedModel && agent?.allowed_models?.includes(selectedModel) ? selectedModel : undefined
      )
    } catch (e) {
      logger.error('Failed to send message', e)
      setIsSending(false)
    }
  }

  const currentSessionName = sessions.find((s) => s.session_id === selectedSessionId)?.name

  return (
    <>
      <Header fixed>
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => router.push('/agents')}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <h1 className="text-xl font-bold truncate">{agent?.name || '로딩 중...'}</h1>
        </div>
        <div className="ms-auto flex items-center space-x-4">
          <ThemeSwitch />
          <ConfigDrawer />
          <ProfileDropdown />
        </div>
      </Header>

      <Main fixed>
        <section className="flex h-full gap-6">
          {/* Session list */}
          <div className="flex w-full flex-col gap-2 sm:w-56 lg:w-72 2xl:w-80">
            <div className="sticky top-0 z-10 -mx-4 bg-background px-4 pb-3 shadow-md sm:static sm:z-auto sm:mx-0 sm:p-0 sm:shadow-none">
              <div className="flex items-center justify-between py-2">
                <div className="flex gap-2 items-center">
                  <h2 className="text-2xl font-bold">채팅</h2>
                  <MessagesSquare size={20} />
                </div>
                <Button size="icon" variant="ghost" onClick={handleCreateSession} title="새 채팅">
                  <Edit size={24} className="stroke-muted-foreground" />
                </Button>
              </div>
            </div>

            <ScrollArea className="-mx-3 h-full overflow-y-auto p-3">
              {sessions.map((session) => (
                <Fragment key={session.session_id}>
                  <div className="group flex items-center gap-2">
                    <button
                      type="button"
                      className={cn(
                        'hover:bg-accent hover:text-accent-foreground flex flex-1 rounded-md px-2 py-2 text-start text-sm',
                        selectedSessionId === session.session_id && 'bg-muted'
                      )}
                      onClick={() => {
                        setSelectedSessionId(session.session_id)
                        setMobileSelectedSessionId(session.session_id)
                      }}
                    >
                      <div className="overflow-hidden text-left">
                        <span className="font-medium truncate block">{session.name || '새 채팅'}</span>
                        <span className="text-xs text-muted-foreground truncate block">
                          {session.session_id.substring(0, 8)}...
                        </span>
                      </div>
                    </button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="opacity-0 group-hover:opacity-100 h-8 w-8"
                      onClick={(e) => {
                        e.stopPropagation()
                        setSessionToDelete(session.session_id)
                        setDeleteDialogOpen(true)
                      }}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                  <Separator className="my-1" />
                </Fragment>
              ))}
              {sessions.length === 0 && (
                <div className="text-center text-muted-foreground py-4 text-sm">채팅이 없습니다</div>
              )}
            </ScrollArea>
          </div>

          {/* Chat area */}
          {selectedSessionId ? (
            <div
              className={cn(
                'absolute inset-0 start-full z-50 hidden w-full flex-1 flex-col border bg-background shadow-xs sm:static sm:z-auto sm:flex sm:rounded-md',
                mobileSelectedSessionId && 'start-0 flex'
              )}
            >
              <div className="mb-1 flex flex-none justify-between bg-card p-4 shadow-lg sm:rounded-t-md">
                <div className="flex gap-3 items-center">
                  <Button size="icon" variant="ghost" className="-ms-2 h-full sm:hidden" onClick={() => setMobileSelectedSessionId(null)}>
                    <ArrowLeft className="rtl:rotate-180" />
                  </Button>
                  <span className="text-sm font-medium lg:text-base">{currentSessionName || '새 채팅'}</span>
                </div>
              </div>

              <ChatArea messages={messages} isLoading={isSending} />

              <div className="p-3 bg-background border-t">
                <form className="flex w-full flex-none gap-2" onSubmit={handleSendMessage}>
                  <div className="flex flex-1 items-center gap-2 rounded-md border border-input bg-card px-2 py-1 focus-within:ring-1 focus-within:ring-ring focus-within:outline-hidden lg:gap-4">
                    <Button
                      size="icon"
                      type="button"
                      variant={isDeepThinking ? 'secondary' : 'ghost'}
                      className={cn('h-8 rounded-md', isDeepThinking && 'bg-blue-100 dark:bg-blue-900')}
                      onClick={() => setIsDeepThinking(!isDeepThinking)}
                      title="Deep Thinking 모드"
                    >
                      <BrainCircuit
                        size={20}
                        className={cn('stroke-muted-foreground', isDeepThinking && 'stroke-blue-600 dark:stroke-blue-400')}
                      />
                    </Button>
                    {agent?.allowed_models && agent.allowed_models.length > 0 && (
                      <Select
                        value={selectedModel ?? agent.allowed_models[0]}
                        onValueChange={setSelectedModel}
                      >
                        <SelectTrigger className="h-7 text-xs border-0 shadow-none bg-transparent px-1 w-auto max-w-40 gap-1 focus:ring-0">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {agent.allowed_models.map((resourceId) => {
                            const found = chatModels.find((m) => String(m.id) === resourceId)
                            return (
                              <SelectItem key={resourceId} value={resourceId} className="text-xs">
                                {found ? found.model_name : resourceId}
                              </SelectItem>
                            )
                          })}
                        </SelectContent>
                      </Select>
                    )}
                    <label className="flex-1">
                      <span className="sr-only">메시지 입력</span>
                      <input
                        type="text"
                        placeholder={`${agent?.name || 'Agent'}에게 메시지 보내기...`}
                        className="h-8 w-full bg-inherit focus-visible:outline-hidden"
                        value={inputMessage}
                        onChange={(e) => setInputMessage(e.target.value)}
                        disabled={isSending}
                      />
                    </label>
                    <Button variant="ghost" size="icon" className="hidden sm:inline-flex" type="submit" disabled={isSending || !inputMessage.trim()}>
                      <Send size={20} />
                    </Button>
                  </div>
                  <Button className="h-full sm:hidden" type="submit" disabled={isSending || !inputMessage.trim()}>
                    <Send size={18} />
                  </Button>
                </form>
              </div>
            </div>
          ) : (
            <div className="absolute inset-0 start-full z-50 hidden w-full flex-1 flex-col justify-center rounded-md border bg-card shadow-xs sm:static sm:z-auto sm:flex">
              <div className="flex flex-col items-center space-y-6">
                <div className="flex size-16 items-center justify-center rounded-full border-2 border-border">
                  <MessagesSquare className="size-8" />
                </div>
                <div className="space-y-2 text-center">
                  <h1 className="text-xl font-semibold">{agent?.name || 'Agent'}</h1>
                  <p className="text-sm text-muted-foreground">
                    {agent?.welcome_message || agent?.description || '새 대화를 시작하세요.'}
                  </p>
                </div>
                <Button onClick={handleCreateSession}>새 채팅 시작</Button>
              </div>
            </div>
          )}
        </section>

        <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>채팅 삭제</DialogTitle>
              <DialogDescription>이 채팅을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.</DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>취소</Button>
              <Button variant="destructive" onClick={handleDeleteSession}>삭제</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </Main>
    </>
  )
}
