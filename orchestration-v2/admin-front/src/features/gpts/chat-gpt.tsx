'use client'

import { useEffect, useState, useRef, Fragment } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { customGptApi, type CustomGPT, type GPTSession } from '@/api/custom-gpts'
import { type Message } from '@/types/chat-api'
import { ChatArea } from '@/features/chats/components/chat-area'
import { Header } from '@/components/layout/header'
import { Main } from '@/components/layout/main'
import { toast } from 'sonner'
import { logger } from '@/lib/logger'
import { ThemeSwitch } from '@/components/theme-switch'
import { ConfigDrawer } from '@/components/config-drawer'
import { ProfileDropdown } from '@/components/profile-dropdown'
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
import {
  ArrowLeft,
  BrainCircuit,
  Edit,
  MessagesSquare,
  Send,
  Trash2,
  X,
  ImageIcon,
  FileText,
} from 'lucide-react'
import { cn } from '@/lib/utils'

export function GptChat() {
  const params = useParams()
  const router = useRouter()
  const gptId = params.gptId as string

  const [gpt, setGpt] = useState<CustomGPT | null>(null)

  // Session list
  const [sessions, setSessions] = useState<GPTSession[]>([])
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null)
  const [mobileSelectedSessionId, setMobileSelectedSessionId] = useState<string | null>(null)

  // Chat
  const [messages, setMessages] = useState<Message[]>([])
  const [isSending, setIsSending] = useState(false)
  const [isDeepThinking, setIsDeepThinking] = useState(false)
  const [inputMessage, setInputMessage] = useState('')
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Delete dialog
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [sessionToDelete, setSessionToDelete] = useState<string | null>(null)

  useEffect(() => {
    if (gptId) {
      loadGpt()
      loadSessions()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gptId])

  // Load messages when session changes
  useEffect(() => {
    if (selectedSessionId) {
      loadMessages(selectedSessionId)
    } else {
      setMessages([])
    }
  }, [selectedSessionId])

  const loadGpt = async () => {
    try {
      const data = await customGptApi.get(gptId)
      setGpt(data)
    } catch (error) {
      logger.error('Failed to load GPT', error)
      toast.error('Failed to load GPT details')
      router.push('/gpts')
    }
  }

  const loadSessions = async () => {
    try {
      const data = await customGptApi.getSessions(gptId)
      setSessions(data)
      // Auto-select the most recent session
      if (data.length > 0) {
        setSelectedSessionId(data[0].session_id)
        setMobileSelectedSessionId(data[0].session_id)
      }
    } catch (error) {
      logger.error('Failed to load GPT sessions', error)
      toast.error('Failed to load chat history')
    }
  }

  const loadMessages = async (sessionId: string) => {
    try {
      const data = await customGptApi.getMessages(gptId, sessionId)
      setMessages(data)
    } catch (error) {
      logger.error('Failed to load GPT messages', error)
      toast.error('Failed to load messages')
    }
  }

  const handleCreateSession = async () => {
    try {
      const newSession = await customGptApi.createSession(gptId)
      setSessions((prev) => [newSession, ...prev])
      setSelectedSessionId(newSession.session_id)
      setMobileSelectedSessionId(newSession.session_id)
      setMessages([])
    } catch (error) {
      logger.error('Failed to create GPT session', error)
      toast.error('Failed to create new chat')
    }
  }

  const handleDeleteSession = async () => {
    if (!sessionToDelete) return
    try {
      await customGptApi.deleteSession(gptId, sessionToDelete)
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionToDelete))
      if (selectedSessionId === sessionToDelete) {
        setSelectedSessionId(null)
        setMobileSelectedSessionId(null)
      }
      setDeleteDialogOpen(false)
      setSessionToDelete(null)
    } catch (error) {
      logger.error('Failed to delete GPT session', error)
      toast.error('Failed to delete session')
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setSelectedFiles((prev) => [...prev, ...Array.from(e.target.files!)])
    }
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const removeFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index))
  }

  const handleSendMessage = async (e?: React.FormEvent) => {
    e?.preventDefault()
    if ((!inputMessage.trim() && selectedFiles.length === 0) || !selectedSessionId || isSending) return

    const contentToSend = inputMessage.trim() || (selectedFiles.length > 0 ? 'Attached file(s)' : '')
    const userMessage: Message = { role: 'user', content: contentToSend }

    setMessages((prev) => [...prev, userMessage, { role: 'assistant', content: '' }])
    setInputMessage('')
    setSelectedFiles([])
    setIsSending(true)

    let currentResponse = ''

    try {
      await customGptApi.streamMessage(
        gptId,
        selectedSessionId,
        [...messages, userMessage],
        (chunk, done, title) => {
          if (title) {
            setSessions((prev) =>
              prev.map((s) =>
                s.session_id === selectedSessionId ? { ...s, name: title } : s
              )
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
          logger.error('Failed to send GPT message', error)
          toast.error('Failed to send message')
          setIsSending(false)
        },
        isDeepThinking
      )
    } catch (error) {
      logger.error('Failed to send GPT message', error)
      toast.error('Failed to send message')
      setIsSending(false)
    }
  }

  const currentSessionName = sessions.find((s) => s.session_id === selectedSessionId)?.name

  return (
    <>
      <Header fixed>
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => router.push('/gpts')}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <h1 className="text-xl font-bold truncate">{gpt?.name || 'Loading...'}</h1>
        </div>
        <div className="ms-auto flex items-center space-x-4">
          <ThemeSwitch />
          <ConfigDrawer />
          <ProfileDropdown />
        </div>
      </Header>

      <Main fixed>
        <section className="flex h-full gap-6">
          {/* ── Left Sidebar: Session list ── */}
          <div className="flex w-full flex-col gap-2 sm:w-56 lg:w-72 2xl:w-80">
            <div className="sticky top-0 z-10 -mx-4 bg-background px-4 pb-3 shadow-md sm:static sm:z-auto sm:mx-0 sm:p-0 sm:shadow-none">
              <div className="flex items-center justify-between py-2">
                <div className="flex gap-2 items-center">
                  <h2 className="text-2xl font-bold">Chats</h2>
                  <MessagesSquare size={20} />
                </div>
                <Button
                  size="icon"
                  variant="ghost"
                  onClick={handleCreateSession}
                  className="rounded-lg"
                  title="New Chat"
                >
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
                        'hover:bg-accent hover:text-accent-foreground',
                        'flex flex-1 rounded-md px-2 py-2 text-start text-sm',
                        selectedSessionId === session.session_id && 'bg-muted'
                      )}
                      onClick={() => {
                        setSelectedSessionId(session.session_id)
                        setMobileSelectedSessionId(session.session_id)
                      }}
                    >
                      <div className="overflow-hidden text-left">
                        <span className="font-medium truncate block">
                          {session.name || 'New Chat'}
                        </span>
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
                <div className="text-center text-muted-foreground py-4 text-sm">
                  No chats yet
                </div>
              )}
            </ScrollArea>
          </div>

          {/* ── Right: Chat area ── */}
          {selectedSessionId ? (
            <div
              className={cn(
                'absolute inset-0 start-full z-50 hidden w-full flex-1 flex-col border bg-background shadow-xs sm:static sm:z-auto sm:flex sm:rounded-md',
                mobileSelectedSessionId && 'start-0 flex'
              )}
            >
              {/* Chat header */}
              <div className="mb-1 flex flex-none justify-between bg-card p-4 shadow-lg sm:rounded-t-md">
                <div className="flex gap-3 items-center">
                  <Button
                    size="icon"
                    variant="ghost"
                    className="-ms-2 h-full sm:hidden"
                    onClick={() => setMobileSelectedSessionId(null)}
                  >
                    <ArrowLeft className="rtl:rotate-180" />
                  </Button>
                  <span className="text-sm font-medium lg:text-base">
                    {currentSessionName || 'New Chat'}
                  </span>
                </div>
              </div>

              {/* Messages */}
              <ChatArea messages={messages} isLoading={isSending} />

              {/* Input */}
              <div className="p-3 bg-background border-t">
                {selectedFiles.length > 0 && (
                  <div className="flex gap-2 mb-2 overflow-x-auto p-1">
                    {selectedFiles.map((file, index) => (
                      <div
                        key={index}
                        className="relative group flex items-center gap-2 bg-muted/50 border rounded-md p-2 pr-6 min-w-[150px] max-w-[200px]"
                      >
                        <div className="flex-shrink-0 text-muted-foreground">
                          {file.type.startsWith('image/') ? (
                            <ImageIcon size={16} />
                          ) : (
                            <FileText size={16} />
                          )}
                        </div>
                        <span className="text-xs truncate flex-1 block" title={file.name}>
                          {file.name}
                        </span>
                        <button
                          type="button"
                          onClick={() => removeFile(index)}
                          className="absolute -top-1.5 -right-1.5 bg-muted text-muted-foreground rounded-full p-0.5 shadow-sm hover:bg-black/90"
                        >
                          <X size={12} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                <form className="flex w-full flex-none gap-2" onSubmit={handleSendMessage}>
                  <input
                    type="file"
                    multiple
                    className="hidden"
                    ref={fileInputRef}
                    onChange={handleFileSelect}
                  />
                  <div className="flex flex-1 items-center gap-2 rounded-md border border-input bg-card px-2 py-1 focus-within:ring-1 focus-within:ring-ring focus-within:outline-hidden lg:gap-4">
                    <Button
                      size="icon"
                      type="button"
                      variant={isDeepThinking ? 'secondary' : 'ghost'}
                      className={cn(
                        'h-8 rounded-md',
                        isDeepThinking && 'bg-blue-100 dark:bg-blue-900'
                      )}
                      onClick={() => setIsDeepThinking(!isDeepThinking)}
                      title="Deep Thinking Mode"
                    >
                      <BrainCircuit
                        size={20}
                        className={cn(
                          'stroke-muted-foreground',
                          isDeepThinking && 'stroke-blue-600 dark:stroke-blue-400'
                        )}
                      />
                    </Button>
                    <label className="flex-1">
                      <span className="sr-only">Chat Text Box</span>
                      <input
                        type="text"
                        placeholder={`Message ${gpt?.name || 'GPT'}...`}
                        className="h-8 w-full bg-inherit focus-visible:outline-hidden"
                        value={inputMessage}
                        onChange={(e) => setInputMessage(e.target.value)}
                        disabled={isSending}
                      />
                    </label>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="hidden sm:inline-flex"
                      type="submit"
                      disabled={isSending || (!inputMessage.trim() && selectedFiles.length === 0)}
                    >
                      <Send size={20} />
                    </Button>
                  </div>
                  <Button
                    className="h-full sm:hidden"
                    type="submit"
                    disabled={isSending || (!inputMessage.trim() && selectedFiles.length === 0)}
                  >
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
                  <h1 className="text-xl font-semibold">{gpt?.name || 'Custom GPT'}</h1>
                  <p className="text-sm text-muted-foreground">
                    {gpt?.description || 'Start a new conversation to begin.'}
                  </p>
                </div>
                <Button onClick={handleCreateSession}>Start New Chat</Button>
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
              <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
                Cancel
              </Button>
              <Button variant="destructive" onClick={handleDeleteSession}>
                Delete
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </Main>
    </>
  )
}
