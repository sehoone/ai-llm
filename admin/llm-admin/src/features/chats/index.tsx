'use client'

import { useState, useEffect, useRef } from 'react'
import { Fragment } from 'react/jsx-runtime'
import {
  ArrowLeft,
  BrainCircuit,
  Edit,
  MessagesSquare,
  Plus,
  Search as SearchIcon,
  Send,
  Trash2,
  X,
  FileText,
  Image as ImageIcon,
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
import { chatService } from '@/api/chat'
import { ChatSession, Message, FileAttachment } from '@/types/chat-api'
import { toast } from 'sonner'

export function Chats() {
  const [search, setSearch] = useState('')
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null)
  const [mobileSelectedSessionId, setMobileSelectedSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isSending, setIsSending] = useState(false)
  const [inputMessage, setInputMessage] = useState('')
  const [isDeepThinking, setIsDeepThinking] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [sessionToDelete, setSessionToDelete] = useState<string | null>(null)
  
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Fetch sessions on mount
  useEffect(() => {
    loadSessions()
  }, [])

  // Fetch messages when session is selected
  useEffect(() => {
    if (selectedSessionId) {
      loadMessages(selectedSessionId)
    } else {
      setMessages([])
    }
  }, [selectedSessionId])

  const loadSessions = async () => {
    try {
      const data = await chatService.getSessions()
      setSessions(data)
    } catch (error) {
      console.error('Failed to load sessions', error)
      toast.error('Failed to load sessions')
    }
  }

  const loadMessages = async (sessionId: string) => {
    setIsLoading(true)
    try {
      const data = await chatService.getMessages(sessionId)
      setMessages(data)
    } catch (error) {
      console.error('Failed to load messages', error)
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
      console.error('Failed to create session', error)
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
      console.error('Failed to delete session', error)
      toast.error('Failed to delete session')
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles = Array.from(e.target.files)
      setSelectedFiles(prev => [...prev, ...newFiles])
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const removeFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index))
  }

  const convertFileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.readAsDataURL(file)
      reader.onload = () => {
         const result = reader.result as string
         const base64 = result.split(',')[1]
         resolve(base64)
      }
      reader.onerror = error => reject(error)
    })
  }

  const handleSendMessage = async (e?: React.FormEvent) => {
    e?.preventDefault()
    if ((!inputMessage.trim() && selectedFiles.length === 0) || !selectedSessionId || isSending) return

    // Convert files to FileAttachment
    const fileAttachments: FileAttachment[] = []
    if (selectedFiles.length > 0) {
      try {
        for (const file of selectedFiles) {
          const base64 = await convertFileToBase64(file)
          fileAttachments.push({
            filename: file.name,
            content_type: file.type,
            data: base64
          })
        }
      } catch (error) {
        console.error('Failed to process files', error)
        toast.error('Failed to process files')
        return
      }
    }

    // Ensure content is not empty if files are present (backend requirement min_length=1)
    const contentToSend = inputMessage.trim() || (fileAttachments.length > 0 ? "Attached file(s)" : "")

    const userMessage: Message = {
      role: 'user',
      content: contentToSend,
      files: fileAttachments.length > 0 ? fileAttachments : undefined
    }

    setMessages((prev) => [...prev, userMessage])
    setInputMessage('')
    setSelectedFiles([])
    setIsSending(true)

    // Optimistic update for assistant message
    const assistantMessageIndex = messages.length + 1
    // We'll append a placeholder message for streaming
    setMessages((prev) => [...prev, { role: 'assistant', content: '' }])

    let currentResponse = ''

    try {
      const messagesToSend = [userMessage]
      await chatService.streamMessage(
        selectedSessionId,
        messagesToSend,
        (chunk, done, title) => {
           if (title) {
             setSessions((prev) => 
               prev.map(session => 
                 session.session_id === selectedSessionId 
                   ? { ...session, name: title } 
                   : session
               )
             );
           }
           currentResponse += chunk
           setMessages((prev) => {
             const newMessages = [...prev]
             // Update the last message (assistant placeholder)
             if (newMessages.length > assistantMessageIndex) {
                 // Ensure we are updating the assistant message we just added
                 // Note: strict mode or rapid updates might cause issues with index relying on closure state without updater function
                 // But using functional update (prev) helps.
                 // We find the last message, which should be the assistant one
                 newMessages[newMessages.length - 1] = {
                    ...newMessages[newMessages.length - 1],
                    content: currentResponse
                 }
             }
             return newMessages
           })
        },
        (error) => {
            console.error(error)
            toast.error('Failed to send message')
        },
        isDeepThinking
      )
    } catch (error) {
      console.error('Failed to send message', error)
      toast.error('Failed to send message')
    } finally {
      setIsSending(false)
    }
  }

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

              {/* Chat Content */}
              <ChatArea messages={messages} isLoading={isSending && messages.length > 0 && messages[messages.length-1].role !== 'assistant'} />

              {/* Input Area */}
              <div className='p-3 bg-background border-t'>
                {/* File Previews */}
                {selectedFiles.length > 0 && (
                  <div className="flex gap-2 mb-2 overflow-x-auto p-1 custom-scrollbar">
                    {selectedFiles.map((file, index) => (
                      <div key={index} className="relative group flex items-center gap-2 bg-muted/50 border rounded-md p-2 pr-6 min-w-[150px] max-w-[200px] mt-1">
                         <div className="flex-shrink-0 text-muted-foreground">
                           {file.type.startsWith('image/') ? <ImageIcon size={16} /> : <FileText size={16} />}
                         </div>
                         <span className="text-xs truncate flex-1 block" title={file.name}>{file.name}</span>
                         <button
                           type="button"
                           onClick={() => removeFile(index)}
                           className="absolute -top-1.5 -right-1.5 bg-muted text-muted-foreground rounded-full p-0.5 shadow-sm hover:bg-black/90 transition-opacity"
                         >
                            <X size={12} />
                         </button>
                      </div>
                    ))}
                  </div>
                )}
                <form
                  className='flex w-full flex-none gap-2'
                  onSubmit={handleSendMessage}
                >
                  <input
                    type="file"
                    multiple
                    className="hidden"
                    ref={fileInputRef}
                    onChange={handleFileSelect}
                  />
                  <div className='flex flex-1 items-center gap-2 rounded-md border border-input bg-card px-2 py-1 focus-within:ring-1 focus-within:ring-ring focus-within:outline-hidden lg:gap-4'>
                    <Button
                        size='icon'
                        type='button'
                        variant='ghost'
                        className='h-8 rounded-md'
                        onClick={() => fileInputRef.current?.click()}
                      >
                        <Plus size={20} className='stroke-muted-foreground' />
                      </Button>
                    <Button
                        size='icon'
                        type='button'
                        variant={isDeepThinking ? 'secondary' : 'ghost'}
                        className={cn('h-8 rounded-md', isDeepThinking && 'bg-blue-100 dark:bg-blue-900')}
                        onClick={() => setIsDeepThinking(!isDeepThinking)}
                        title="심층사고 모드"
                      >
                        <BrainCircuit size={20} className={cn('stroke-muted-foreground', isDeepThinking && 'stroke-blue-600 dark:stroke-blue-400')} />
                      </Button>
                    <label className='flex-1'>
                      <span className='sr-only'>Chat Text Box</span>
                      <input
                        type='text'
                        placeholder='Type your message...'
                        className='h-8 w-full bg-inherit focus-visible:outline-hidden'
                        value={inputMessage}
                        onChange={(e) => setInputMessage(e.target.value)}
                        disabled={isSending}
                      />
                    </label>
                    <Button
                      variant='ghost'
                      size='icon'
                      className='hidden sm:inline-flex'
                      type="submit"
                      disabled={isSending}
                    >
                      <Send size={20} />
                    </Button>
                  </div>
                  <Button className='h-full sm:hidden' type="submit" disabled={isSending}>
                    <Send size={18} />
                  </Button>
                </form>
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

      </Main>
    </>
  )
}
