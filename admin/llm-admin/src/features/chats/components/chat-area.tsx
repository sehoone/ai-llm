import { useEffect, useRef, useState } from 'react'
import { Message } from '@/types/chat-api'
import { cn } from '@/lib/utils'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Bot, ChevronDown, ChevronRight, User, BrainCircuit, CheckCircle2, Loader2, FileText, Image as ImageIcon } from 'lucide-react'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { markdownComponents } from '@/components/markdown-components'

interface ChatAreaProps {
  messages: Message[]
  isLoading: boolean
}

const DeepThinkingAccordion = ({ thoughts, isThinking }: { thoughts: { title: string; content: string }[]; isThinking: boolean }) => {
  const [isOpen, setIsOpen] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);
  
  // Auto-collapse when thinking finishes (answer starts)
  useEffect(() => {
    if (!isThinking) {
        setIsOpen(false);
    } else {
        setIsOpen(true);
    }
  }, [isThinking]);

  // Auto-scroll to bottom while thinking
  useEffect(() => {
    if (isThinking && isOpen && scrollRef.current) {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [thoughts, isThinking, isOpen]);

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen} className="w-full mb-2 group">
        <CollapsibleTrigger className={cn(
            "flex items-center gap-2 py-2 px-1 w-full rounded-md transition-colors",
             isOpen ? "bg-muted/20" : "hover:bg-muted/10 text-muted-foreground"
            )}>
            <div className={cn("flex items-center justify-center w-5 h-5 rounded-full", isThinking ? "animate-pulse bg-blue-100 dark:bg-blue-900" : "")}>
                {isThinking ? (
                    <Loader2 className="h-3 w-3 text-blue-600 dark:text-blue-400 animate-spin" /> 
                ) : (
                     <BrainCircuit className="h-3.5 w-3.5" />
                )}
            </div>
            
            <span className={cn("text-sm font-medium", isThinking ? "text-foreground" : "text-muted-foreground")}>
                {isThinking ? "Thinking..." : "Thought Process"}
            </span>
            
            <span className="text-xs text-muted-foreground ml-auto flex items-center gap-1">
                 {!isThinking && <span className="text-[10px] bg-muted px-1.5 py-0.5 rounded-full">{thoughts.length} steps</span>}
                 {isOpen ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
            </span>
        </CollapsibleTrigger>
        <CollapsibleContent>
            <div ref={scrollRef} className="pl-2 pr-2 py-2 space-y-3 border-l-2 border-muted ml-2.5 my-1 max-h-60 overflow-y-auto custom-scrollbar">
                {thoughts.map((step, index) => (
                    <div key={index} className="animate-in fade-in slide-in-from-top-1 duration-300">
                        <div className="flex items-center gap-2 mb-1.5">
                             <CheckCircle2 className="h-3 w-3 text-green-500" />
                             <span className="text-xs font-semibold text-foreground/80 first-letter:uppercase">{step.title}</span>
                        </div>
                        <div className="text-sm text-muted-foreground pl-5 whitespace-pre-wrap leading-relaxed opacity-90">
                            <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>{step.content}</ReactMarkdown>
                        </div>
                    </div>
                ))}
            </div>
        </CollapsibleContent>
    </Collapsible>
  );
};

const AssistantMessage = ({ content }: { content: string }) => {
    // Regex iteration approach for robustness
    const thoughts: { title: string; content: string }[] = [];
    let answer = '';
    
    // Match tags like [Deep Thinking - Analysis]
    const tagRegex = /\[Deep Thinking - ([^\]]+)\]/gi;
    let match;
    let lastIndex = 0;
    let currentTitle = '';
    
    while ((match = tagRegex.exec(content)) !== null) {
        // Content before the current tag
        const segment = content.substring(lastIndex, match.index);
        
        if (segment) {
             if (currentTitle === 'answer') {
                answer += segment;
            } else if (currentTitle) {
                thoughts.push({ title: currentTitle, content: segment.trim() });
            } else {
                // Before any tag -> Answer (Preamble / Orphan text)
                if (segment.trim()) {
                    answer += segment;
                }
            }
        }
        
        // Update title for the *next* segment
        currentTitle = match[1].trim().toLowerCase();
        lastIndex = tagRegex.lastIndex;
    }
    
    // Remaining content after last tag
    const remaining = content.substring(lastIndex);
    if (remaining) {
        if (currentTitle === 'answer') {
            answer += remaining;
        } else if (currentTitle) {
            thoughts.push({ title: currentTitle, content: remaining.trim() });
        } else {
            if (remaining.trim()) {
                answer += remaining;
            }
        }
    }

    const hasAnswerTag = /\[Deep Thinking - Answer\]/i.test(content);
    const isThinking = thoughts.length > 0 && !hasAnswerTag;

    // Fallback: If no thoughts and no answer logic triggered, just show content
    if (thoughts.length === 0 && !hasAnswerTag) {
         return <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>{content}</ReactMarkdown>;
    }

    return (
        <div className="space-y-2">
            {thoughts.length > 0 && (
                <DeepThinkingAccordion 
                    thoughts={thoughts} 
                    isThinking={isThinking}
                />
            )}
            {(answer || hasAnswerTag) && (
                <div className="prose dark:prose-invert max-w-none animate-in fade-in duration-700 delay-150">
                    <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>{answer}</ReactMarkdown>
                </div>
            )}
        </div>
    );
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
              <div className='prose break-words dark:prose-invert max-w-none'>
                {message.role === 'user' ? (
                  <div className="space-y-2">
                     <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
                     {message.files && message.files.length > 0 && (
                        <div className="flex flex-wrap gap-2 mt-2">
                            {message.files.map((file, i) => (
                                <div key={i} className="flex items-center gap-2 p-2 bg-background border rounded-md text-sm text-muted-foreground w-fit max-w-full">
                                    {file.content_type.startsWith('image/') ? <ImageIcon className="h-4 w-4 shrink-0" /> : <FileText className="h-4 w-4 shrink-0" />}
                                    <span className="truncate max-w-[200px]" title={file.filename}>{file.filename}</span>
                                </div>
                            ))}
                        </div>
                     )}
                  </div>
                ) : (
                  <AssistantMessage content={message.content} />
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
