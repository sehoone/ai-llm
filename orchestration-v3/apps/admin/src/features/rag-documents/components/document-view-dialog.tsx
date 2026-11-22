import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Loader2, FileText } from 'lucide-react'
import { type DocumentDetailResponse } from '@/api/rag'

interface DocumentViewDialogProps {
  isOpen: boolean
  onOpenChange: (open: boolean) => void
  viewDoc: DocumentDetailResponse | null
  viewLoading: boolean
  formatFileSize: (bytes: number) => string
}

export function DocumentViewDialog({
  isOpen,
  onOpenChange,
  viewDoc,
  viewLoading,
  formatFileSize,
}: DocumentViewDialogProps) {
  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className='max-w-3xl h-[80vh] flex flex-col'>
        <DialogHeader>
          <DialogTitle className='flex items-center gap-2'>
            <FileText className='h-5 w-5 text-blue-500' />
            {viewDoc ? viewDoc.filename : 'Loading...'}
          </DialogTitle>
          <DialogDescription>
            {viewDoc
              ? `Size: ${formatFileSize(viewDoc.size)}`
              : 'Fetching content...'}
          </DialogDescription>
        </DialogHeader>
        <div className='flex-1 overflow-hidden p-4 border rounded-md bg-muted/30'>
          {viewLoading ? (
            <div className='flex h-full items-center justify-center'>
              <Loader2 className='h-8 w-8 animate-spin text-muted-foreground' />
            </div>
          ) : (
            <ScrollArea className='h-full w-full'>
              <pre className='text-sm whitespace-pre-wrap font-mono p-2'>
                {viewDoc?.content || 'No content available'}
              </pre>
            </ScrollArea>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
