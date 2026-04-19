'use client'

import { useState, useRef } from 'react'
import { Plus, Send, BrainCircuit, X, FileText, Image as ImageIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface ChatInputProps {
  isSending: boolean
  onSend: (message: string, files: File[], isDeepThinking: boolean) => void
}

export function ChatInput({ isSending, onSend }: ChatInputProps) {
  const [inputMessage, setInputMessage] = useState('')
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [isDeepThinking, setIsDeepThinking] = useState(true)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setSelectedFiles(prev => [...prev, ...Array.from(e.target.files!)])
    }
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const removeFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index))
  }

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault()
    if ((!inputMessage.trim() && selectedFiles.length === 0) || isSending) return
    onSend(inputMessage, selectedFiles, isDeepThinking)
    setInputMessage('')
    setSelectedFiles([])
  }

  return (
    <div className='p-3 bg-background border-t'>
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
      <form className='flex w-full flex-none gap-2' onSubmit={handleSubmit}>
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
  )
}
