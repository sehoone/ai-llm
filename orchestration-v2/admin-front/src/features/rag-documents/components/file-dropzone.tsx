import { useState } from 'react'
import { FileText, Upload, X } from 'lucide-react'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'

interface FileDropzoneProps {
  files: File[]
  setFiles: (files: File[]) => void
}

function formatBytes(bytes: number, decimals = 2) {
  if (!+bytes) return '0 Bytes'

  const k = 1024
  const dm = decimals < 0 ? 0 : decimals
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']

  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`
}

export function FileDropzone({ files, setFiles }: FileDropzoneProps) {
  const [isDragging, setIsDragging] = useState(false)

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const mergeFiles = (incoming: File[]) => {
    const existingNames = new Set(files.map((f) => f.name))
    return incoming.filter((f) => !existingNames.has(f.name))
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const newFiles = mergeFiles(Array.from(e.dataTransfer.files))
      if (newFiles.length > 0) setFiles([...files, ...newFiles])
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const newFiles = mergeFiles(Array.from(e.target.files))
      if (newFiles.length > 0) setFiles([...files, ...newFiles])
      e.target.value = ''
    }
  }

  const removeFile = (index: number) => {
    setFiles(files.filter((_, i) => i !== index))
  }

  return (
    <div className='space-y-2'>
      <Label htmlFor='file-upload'>Files</Label>
      <div className='flex items-center justify-center w-full'>
        <label
          htmlFor='file-upload'
          className={`flex flex-col items-center justify-center w-full h-32 border-2 border-dashed rounded-lg cursor-pointer bg-gray-50 dark:hover:bg-bray-800 dark:bg-gray-700 hover:bg-gray-100 dark:border-gray-600 dark:hover:border-gray-500 dark:hover:bg-gray-600 ${
            isDragging
              ? 'border-primary bg-primary/10 ring-2 ring-primary ring-offset-2'
              : ''
          }`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <div className='flex flex-col items-center justify-center pt-5 pb-6'>
            <Upload className='w-8 h-8 mb-2 text-gray-500 dark:text-gray-400' />
            <p className='mb-2 text-sm text-gray-500 dark:text-gray-400'>
              <span className='font-semibold'>Click to upload</span> or drag and drop
            </p>
            <p className='text-xs text-gray-500 dark:text-gray-400'>
              PDF, DOCX, TXT, MD (MAX. 10MB per file)
            </p>
          </div>
          <input
            id='file-upload'
            type='file'
            multiple
            className='hidden'
            onChange={handleFileChange}
            accept='.pdf,.docx,.doc,.txt,.md'
          />
        </label>
      </div>
      {files.length > 0 && (
        <div className='space-y-1 mt-2'>
          <p className='text-xs text-muted-foreground'>{files.length}개 파일 선택됨</p>
          <div className='space-y-1 max-h-40 overflow-y-auto'>
            {files.map((f, i) => (
              <div key={i} className='flex items-center justify-between p-2 bg-muted rounded-md text-sm'>
                <div className='flex items-center gap-2 min-w-0'>
                  <FileText className='w-4 h-4 shrink-0 text-primary' />
                  <span className='truncate'>{f.name}</span>
                  <span className='text-xs text-muted-foreground shrink-0'>{formatBytes(f.size)}</span>
                </div>
                <Button
                  type='button'
                  variant='ghost'
                  size='sm'
                  className='h-6 w-6 p-0 shrink-0 ml-2'
                  onClick={() => removeFile(i)}
                >
                  <X className='w-3 h-3' />
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
