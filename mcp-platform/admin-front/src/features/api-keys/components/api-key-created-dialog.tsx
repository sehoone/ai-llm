'use client'

import { useState } from 'react'
import { Copy, Check, TriangleAlert } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

interface ApiKeyCreatedDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  apiKey: string
  keyName: string
}

export function ApiKeyCreatedDialog({
  open,
  onOpenChange,
  apiKey,
  keyName,
}: ApiKeyCreatedDialogProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(apiKey).catch(() => {
      const el = document.createElement('textarea')
      el.value = apiKey
      el.style.position = 'fixed'
      el.style.opacity = '0'
      document.body.appendChild(el)
      el.select()
      document.execCommand('copy')
      document.body.removeChild(el)
    })
    setCopied(true)
    toast.success('API Key copied to clipboard')
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(state) => {
        if (!state) setCopied(false)
        onOpenChange(state)
      }}
    >
      <DialogContent className='sm:max-w-[500px]'>
        <DialogHeader>
          <DialogTitle>API Key Created</DialogTitle>
          <DialogDescription>
            Your new key <strong>{keyName}</strong> has been created. Copy it
            now — it will not be shown again.
          </DialogDescription>
        </DialogHeader>

        <div className='rounded-md border bg-muted p-3'>
          <div className='flex items-center justify-between gap-2'>
            <code className='flex-1 overflow-x-auto text-xs break-all font-mono'>
              {apiKey}
            </code>
            <Button
              variant='ghost'
              size='icon'
              className='shrink-0'
              onClick={handleCopy}
            >
              {copied ? (
                <Check className='h-4 w-4 text-green-500' />
              ) : (
                <Copy className='h-4 w-4' />
              )}
              <span className='sr-only'>Copy</span>
            </Button>
          </div>
        </div>

        <div className='flex items-start gap-2 rounded-md border border-yellow-200 bg-yellow-50 p-3 text-sm text-yellow-800 dark:border-yellow-800 dark:bg-yellow-950 dark:text-yellow-200'>
          <TriangleAlert className='mt-0.5 h-4 w-4 shrink-0' />
          <p>
            This key will only be displayed once. Store it somewhere safe. If
            you lose it, you will need to create a new key.
          </p>
        </div>

        <DialogFooter>
          <Button onClick={() => onOpenChange(false)}>Done</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
