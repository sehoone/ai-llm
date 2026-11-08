'use client'

import { useState, useEffect, useCallback } from 'react'
import { Fragment } from 'react/jsx-runtime'
import {
  ArrowLeft,
  Edit,
  MessagesSquare,
  Search as SearchIcon,
  Trash2,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
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
import { ConfigDrawer } from '@/components/config-drawer'
import { Header } from '@/components/layout/header'
import { Main } from '@/components/layout/main'
import { ProfileDropdown } from '@/components/profile-dropdown'
import { Search } from '@/components/search'
import { ThemeSwitch } from '@/components/theme-switch'
import { ChatArea } from './components/chat-area'
import { ChatInput } from './components/chat-input'
import { ArtifactPanel } from '@/features/artifacts/components/artifact-panel'
import { chatService } from '@/api/chat'
import { artifactService } from '@/api/artifacts'
import { ragGroupApi, type RagGroup } from '@/api/rag-groups'
import { getChatModels, type ChatModel } from '@/api/llm-resources'
import {
  type ChatSession,
  type Message,
  type ApprovalRequiredEvent,
  type ApprovalDecision,
  type ChatStreamCallbacks,
  type FileAttachment,
  type StreamPhase,
} from '@/types/chat-api'
import { useArtifactStore } from '@/stores/artifact-store'
import { toast } from 'sonner'
import { logger } from '@/lib/logger'

export function Chats() {
  const [search, setSearch] = useState('')
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null)
  const [mobileSelectedSessionId, setMobileSelectedSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [, setIsLoading] = useState(false)
  const [isSending, setIsSending] = useState(false)
  // 첫 토큰 이전 서버 진행 단계 (ADR-0011 §5). null이면 표시 안 함.
  const [streamPhase, setStreamPhase] = useState<{ phase: StreamPhase; filename?: string | null } | null>(null)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [sessionToDelete, setSessionToDelete] = useState<string | null>(null)
  const [ragGroups, setRagGroups] = useState<RagGroup[]>([])
  const [selectedRagGroup, setSelectedRagGroup] = useState<string | null>(null)
  const [chatModels, setChatModels] = useState<ChatModel[]>([])
  const [selectedModelId, setSelectedModelId] = useState<number | null>(null)
  const [pendingApproval, setPendingApproval] = useState<{
    ev: ApprovalRequiredEvent
    sessionId: string
  } | null>(null)

  const isArtifactOpen = useArtifactStore((s) => s.isOpen)

  // Fetch sessions, RAG groups, and chat models on mount
  useEffect(() => {
    loadSessions()
    loadRagGroups()
    loadChatModels()
  }, [])

  // Deep link from the Artifacts library: /chats?session=<id> selects that session.
  useEffect(() => {
    const sessionParam = new URLSearchParams(window.location.search).get('session')
    if (sessionParam) {
      setSelectedSessionId(sessionParam)
      setMobileSelectedSessionId(sessionParam)
    }
  }, [])

  // Fetch messages when session is selected; reset the artifact canvas per session.
  useEffect(() => {
    useArtifactStore.getState().reset()
    if (selectedSessionId) {
      loadMessages(selectedSessionId)
    } else {
      setMessages([])
    }
  }, [selectedSessionId])

  // Open an artifact referenced from a chat message, loading it if not cached.
  const handleOpenArtifact = useCallback(
    async (identifier: string) => {
      const store = useArtifactStore.getState()
      if (store.artifacts[identifier]?.content) {
        store.open(identifier)
        return
      }
      if (!selectedSessionId) return
      try {
        const summaries = await artifactService.list(selectedSessionId)
        const match = summaries.find((s) => s.identifier === identifier)
        if (!match) {
          toast.error('아티펙트를 찾을 수 없습니다')
          return
        }
        const detail = await artifactService.get(match.id)
        store.upsertArtifact({
          identifier: detail.identifier,
          type: detail.artifact_type,
          title: detail.title,
          content: detail.content,
          version: detail.current_version,
          isStreaming: false,
          serverId: detail.id,
        })
        store.open(identifier)
      } catch (error) {
        logger.error('Failed to open artifact', error)
        toast.error('아티펙트를 불러오지 못했습니다')
      }
    },
    [selectedSessionId]
  )

  const loadSessions = async () => {
    try {
      const data = await chatService.getSessions()
      setSessions(data)
    } catch (error) {
      logger.error('Failed to load sessions', error)
      toast.error('Failed to load sessions')
    }
  }

  // RAG 그룹 로드 (ADR-0012 Phase 2b). 실패는 비치명적(토스트 없음) — chat은 RAG 없이도 동작.
  const loadRagGroups = async () => {
    try {
      const data = await ragGroupApi.listGroups()
      setRagGroups(data)
    } catch (error) {
      logger.error('Failed to load RAG groups', error)
    }
  }

  const loadChatModels = async () => {
    try {
      const data = await getChatModels()
      setChatModels(data)
      // llm_resource(chat 모델)가 있으면 첫 항목을 기본 선택 — "서버 기본값" 대신 DB 리소스 우선.
      if (data.length > 0) {
        setSelectedModelId((prev) => prev ?? data[0].id)
      }
    } catch (error) {
      logger.error('Failed to load chat models', error)
    }
  }

  const loadMessages = async (sessionId: string) => {
    setIsLoading(true)
    try {
      const data = await chatService.getMessages(sessionId)
      setMessages(data)
    } catch (error) {
      logger.error('Failed to load messages', error)
      toast.error('Failed to load messages')
    } finally {
      setIsLoading(false)
    }
  }

  const handleCreateSession = async () => {
    try {
      const newSession = await chatService.createSession()
      setSessions((prev) => [newSession, ...prev])
      setSelectedSessionId(newSession.session_id)
      setMobileSelectedSessionId(newSession.session_id)
      setMessages([])
    } catch (error) {
      logger.error('Failed to create session', error)
      toast.error('Failed to create new chat')
    }
  }

  const handleDeleteSession = async () => {
    if (!sessionToDelete) return
    try {
      await chatService.deleteSession(sessionToDelete)
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionToDelete))
      if (selectedSessionId === sessionToDelete) {
        setSelectedSessionId(null)
        setMobileSelectedSessionId(null)
      }
      setDeleteDialogOpen(false)
      setSessionToDelete(null)
    } catch (error) {
      logger.error('Failed to delete session', error)
      toast.error('Failed to delete session')
    }
  }

  // v3 chat SSE 콜백 (ADR-0008). assistant message는 마지막 placeholder에 이어붙이고,
  // CONFIRM 티어 tool call을 만나면 승인 다이얼로그를 띄운다.
  const appendToAssistant = (text: string) => {
    if (!text) return
    setMessages((prev) => {
      const next = [...prev]
      const last = next[next.length - 1]
      if (last && last.role === 'assistant') {
        next[next.length - 1] = { ...last, content: (last.content || '') + text }
      } else {
        next.push({ role: 'assistant', content: text })
      }
      return next
    })
  }

  const makeStreamCallbacks = useCallback(
    (sessionId: string): ChatStreamCallbacks => ({
      // 진행 단계 신호 (ADR-0011 §5) — 첫 토큰 이전 업로드/추출/생성 단계 표시.
      onStatus: (phase, filename) => setStreamPhase({ phase, filename }),
      // 토큰 스트리밍 — assistant 버블에 이어붙임 (ADR-0011). 첫 토큰에 진행 표시 해제.
      onContent: (delta) => {
        setStreamPhase(null)
        appendToAssistant(delta)
      },
      // 비스트리밍 완결 메시지(tool 결과는 표시 안 함; assistant 폴백만 반영).
      onMessage: (msg) => {
        setStreamPhase(null)
        if (msg.role === 'assistant' && msg.content) appendToAssistant(msg.content)
      },
      // 아티팩트 스트리밍 — 캔버스 스토어 구동 (ADR-0013).
      onArtifact: (event) => {
        if (event.kind === 'start') setStreamPhase(null)
        const store = useArtifactStore.getState()
        if (event.kind === 'start') {
          store.startArtifact({ identifier: event.identifier, type: event.type, title: event.title })
        } else if (event.kind === 'delta') {
          store.appendDelta(event.identifier, event.text)
        } else if (event.kind === 'end') {
          store.endArtifact(event.identifier, event.version)
        }
      },
      onApprovalRequired: (ev) => {
        setStreamPhase(null)
        setPendingApproval({ ev, sessionId })
        setIsSending(false)
      },
      // 첫 대화 자동 제목 — 세션 목록 이름 갱신.
      onTitle: (title) => {
        if (!title) return
        setSessions((prev) =>
          prev.map((s) => (s.session_id === sessionId ? { ...s, name: title } : s))
        )
      },
      onDone: () => {
        setStreamPhase(null)
        setIsSending(false)
      },
      onError: (error) => {
        setStreamPhase(null)
        logger.error('Chat stream error', error)
        toast.error('Failed to send message')
        setIsSending(false)
      },
    }),
    []
  )

  // 스트리밍 중 생성된 아티팩트에 서버 id/버전을 해소(버전관리·공개용) — ADR-0013.
  const syncArtifactServerIds = useCallback(async (sessionId: string) => {
    try {
      const summaries = await artifactService.list(sessionId)
      const store = useArtifactStore.getState()
      for (const s of summaries) {
        const existing = store.artifacts[s.identifier]
        if (existing) {
          store.upsertArtifact({ ...existing, serverId: s.id, version: s.current_version })
        }
      }
    } catch (error) {
      logger.error('Failed to sync artifact server ids', error)
    }
  }, [])

  const convertFileToBase64 = (file: File): Promise<string> =>
    new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve((reader.result as string).split(',')[1])
      reader.onerror = reject
      reader.readAsDataURL(file)
    })

  // NOTE: deep thinking은 아직 미지원 — 해당 인자는 무시. 첨부는 ADR-0014(이미지 비전·텍스트).
  const handleSendMessage = useCallback(
    async (inputMessage: string, selectedFiles: File[], _isDeepThinking: boolean) => {
      const content = inputMessage.trim()
      if ((!content && selectedFiles.length === 0) || !selectedSessionId || isSending) return

      let files: FileAttachment[] | undefined
      if (selectedFiles.length > 0) {
        try {
          files = await Promise.all(
            selectedFiles.map(async (f) => ({
              filename: f.name,
              content_type: f.type,
              data: await convertFileToBase64(f),
            }))
          )
        } catch (error) {
          logger.error('Failed to process files', error)
          toast.error('Failed to process files')
          return
        }
      }

      const text = content || (files ? 'Attached file(s)' : '')
      const userMessage: Message = { role: 'user', content: text, files }
      setMessages((prev) => [...prev, userMessage, { role: 'assistant', content: '' }])
      setIsSending(true)
      // 낙관적 진행 표시 — 서버 status 이벤트 도착 전까지의 공백 제거 (ADR-0011 §5).
      setStreamPhase({ phase: files && files.length > 0 ? 'uploading' : 'thinking' })

      await chatService.streamMessage(
        selectedSessionId,
        text,
        makeStreamCallbacks(selectedSessionId),
        selectedModelId ?? undefined,
        selectedRagGroup ?? undefined,
        files
      )
      // 스트림 종료 — 이번 턴 아티팩트의 서버 id/버전 해소.
      await syncArtifactServerIds(selectedSessionId)
    },
    [selectedSessionId, isSending, makeStreamCallbacks, selectedModelId, selectedRagGroup, syncArtifactServerIds]
  )

  // 승인/거부 → 그래프 재개 (ADR-0008 §4). 현재 UI는 그룹 단위 일괄 결정.
  const handleApprovalDecision = useCallback(
    async (approved: boolean) => {
      if (!pendingApproval) return
      const { ev, sessionId } = pendingApproval
      const decisions: ApprovalDecision[] = ev.requests.map((r) => ({
        tool_call_id: r.tool_call_id,
        approved,
      }))
      setPendingApproval(null)
      setIsSending(true)
      await chatService.submitApprovals(sessionId, ev.group_key, decisions, makeStreamCallbacks(sessionId))
    },
    [pendingApproval, makeStreamCallbacks]
  )

  const filteredSessions = sessions.filter((s) =>
    (s.name || 'New Chat').toLowerCase().includes(search.trim().toLowerCase())
  )

  return (
    <>
      <Header>
        <Search />
        <div className='ms-auto flex items-center space-x-4'>
          <ThemeSwitch />
          <ConfigDrawer />
          <ProfileDropdown />
        </div>
      </Header>

      <Main fixed>
        <section className='flex h-full gap-6'>
          {/* Left Side - Session List */}
          <div className='flex w-full flex-col gap-2 sm:w-56 lg:w-72 2xl:w-80'>
            <div className='sticky top-0 z-10 -mx-4 bg-background px-4 pb-3 shadow-md sm:static sm:z-auto sm:mx-0 sm:p-0 sm:shadow-none'>
              <div className='flex items-center justify-between py-2'>
                <div className='flex gap-2'>
                  <h1 className='text-2xl font-bold'>Chats</h1>
                  <MessagesSquare size={20} />
                </div>

                <Button
                  size='icon'
                  variant='ghost'
                  onClick={handleCreateSession}
                  className='rounded-lg'
                >
                  <Edit size={24} className='stroke-muted-foreground' />
                </Button>
              </div>

              <label
                className={cn(
                  'focus-within:ring-1 focus-within:ring-ring focus-within:outline-hidden',
                  'flex h-10 w-full items-center space-x-0 rounded-md border border-border ps-2'
                )}
              >
                <SearchIcon size={15} className='me-2 stroke-slate-500' />
                <span className='sr-only'>Search</span>
                <input
                  type='text'
                  className='w-full flex-1 bg-inherit text-sm focus-visible:outline-hidden'
                  placeholder='Search chat...'
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </label>
            </div>

            <ScrollArea className='-mx-3 h-full overflow-y-auto p-3'>
              {filteredSessions.map((session) => (
                <Fragment key={session.session_id}>
                  <div className='group flex items-center gap-2'>
                     <button
                      type='button'
                      className={cn(
                        'hover:bg-accent hover:text-accent-foreground',
                        `flex flex-1 rounded-md px-2 py-2 text-start text-sm`,
                        selectedSessionId === session.session_id && 'bg-muted'
                      )}
                      onClick={() => {
                        setSelectedSessionId(session.session_id)
                        setMobileSelectedSessionId(session.session_id)
                      }}
                    >
                      <div className='flex gap-2 items-center'>
                        <Avatar className='h-8 w-8'>
                          <AvatarFallback>{(session.name || 'NC').substring(0, 2).toUpperCase()}</AvatarFallback>
                        </Avatar>
                        <div className='overflow-hidden text-left'>
                          <span className='font-medium truncate block'>
                            {session.name || 'New Chat'}
                          </span>
                          <span className='text-xs text-muted-foreground truncate block'>
                             {session.session_id.substring(0, 8)}...
                          </span>
                        </div>
                      </div>
                    </button>
                     <Button
                        variant="ghost"
                        size="icon"
                        className="opacity-0 group-hover:opacity-100 h-8 w-8"
                        onClick={(e) => {
                            e.stopPropagation();
                            setSessionToDelete(session.session_id);
                            setDeleteDialogOpen(true);
                        }}
                    >
                        <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                  <Separator className='my-1' />
                </Fragment>
              ))}
              {filteredSessions.length === 0 && (
                 <div className="text-center text-muted-foreground py-4 text-sm">
                    No chats found
                 </div>
              )}
            </ScrollArea>
          </div>

          {/* Right Side - Chat Area */}
          {selectedSessionId ? (
            <div
              className={cn(
                'absolute inset-0 start-full z-50 hidden w-full flex-1 flex-col border bg-background shadow-xs sm:static sm:z-auto sm:flex sm:rounded-md',
                mobileSelectedSessionId && 'start-0 flex'
              )}
            >
              {/* Header */}
              <div className='mb-1 flex flex-none justify-between bg-card p-4 shadow-lg sm:rounded-t-md'>
                <div className='flex gap-3 items-center'>
                  <Button
                    size='icon'
                    variant='ghost'
                    className='-ms-2 h-full sm:hidden'
                    onClick={() => setMobileSelectedSessionId(null)}
                  >
                    <ArrowLeft className='rtl:rotate-180' />
                  </Button>
                  <div className='flex items-center gap-2 lg:gap-4'>
                    <Avatar className='size-9 lg:size-11'>
                       <AvatarFallback>AI</AvatarFallback>
                    </Avatar>
                    <div>
                      <span className='text-sm font-medium lg:text-base'>
                        {sessions.find(s => s.session_id === selectedSessionId)?.name || 'New Chat'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Chat + Artifact canvas (split on wide screens, overlay on narrow) */}
              <div className='relative flex min-h-0 flex-1'>
                <div className='flex min-w-0 flex-1 flex-col'>
                  <ChatArea
                    messages={messages}
                    isLoading={isSending && messages.length > 0 && messages[messages.length-1].role !== 'assistant'}
                    streamPhase={streamPhase}
                    onOpenArtifact={handleOpenArtifact}
                  />
                  <ChatInput
                    isSending={isSending}
                    onSend={handleSendMessage}
                    ragGroups={ragGroups}
                    selectedRagGroup={selectedRagGroup}
                    onRagGroupChange={setSelectedRagGroup}
                    chatModels={chatModels}
                    selectedModelId={selectedModelId}
                    onModelChange={setSelectedModelId}
                  />
                </div>

                {isArtifactOpen && (
                  // Narrow screens: full overlay over the chat. Wide (md+): side-by-side.
                  <div className='absolute inset-0 z-30 bg-background p-2 md:static md:z-auto md:min-w-0 md:flex-1 lg:flex-[1.3]'>
                    <ArtifactPanel />
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div
              className={cn(
                'absolute inset-0 start-full z-50 hidden w-full flex-1 flex-col justify-center rounded-md border bg-card shadow-xs sm:static sm:z-auto sm:flex'
              )}
            >
              <div className='flex flex-col items-center space-y-6'>
                <div className='flex size-16 items-center justify-center rounded-full border-2 border-border'>
                  <MessagesSquare className='size-8' />
                </div>
                <div className='space-y-2 text-center'>
                  <h1 className='text-xl font-semibold'>Welcome to LLM Chat</h1>
                  <p className='text-sm text-muted-foreground'>
                    Start a new conversation to begin.
                  </p>
                </div>
                <Button onClick={handleCreateSession}>
                  Start New Chat
                </Button>
              </div>
            </div>
          )}
        </section>

        {/* Delete Dialog */}
        <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Delete Chat</DialogTitle>
                    <DialogDescription>
                        Are you sure you want to delete this chat? This action cannot be undone.
                    </DialogDescription>
                </DialogHeader>
                <DialogFooter>
                    <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
                    <Button variant="destructive" onClick={handleDeleteSession}>Delete</Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>

        {/* Approval (HITL) Dialog — ADR-0008 */}
        <Dialog
          open={!!pendingApproval}
          onOpenChange={(open) => { if (!open) setPendingApproval(null) }}
        >
          <DialogContent>
            <DialogHeader>
              <DialogTitle>도구 실행 승인</DialogTitle>
              <DialogDescription>
                아래 작업 실행에 사용자 승인이 필요합니다.
              </DialogDescription>
            </DialogHeader>
            <div className='space-y-3'>
              {pendingApproval?.ev.requests.map((r) => (
                <div key={r.tool_call_id} className='rounded-md border p-3 text-sm'>
                  <div className='font-medium'>{r.name}</div>
                  {r.reason && (
                    <div className='text-xs text-muted-foreground'>{r.reason}</div>
                  )}
                  <pre className='mt-2 overflow-x-auto rounded bg-muted p-2 text-xs'>
                    {JSON.stringify(r.args, null, 2)}
                  </pre>
                </div>
              ))}
            </div>
            <DialogFooter>
              <Button variant='outline' onClick={() => handleApprovalDecision(false)}>거부</Button>
              <Button onClick={() => handleApprovalDecision(true)}>승인</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

      </Main>
    </>
  )
}
