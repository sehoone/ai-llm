import { useState } from 'react'
import { FileText, Upload } from 'lucide-react'
import { Label } from '@/components/ui/label'

interface FileDropzoneProps {
  file: File | null
  setFile: (file: File | null) => void
}

function formatBytes(bytes: number, decimals = 2) {
  if (!+bytes) return '0 Bytes'

  const k = 1024
  const dm = decimals < 0 ? 0 : decimals
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']

  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`
}

export function FileDropzone({ file, setFile }: FileDropzoneProps) {
  const [isDragging, setIsDragging] = useState(false)

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0])
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
    }
  }

  return (
    <div className='space-y-2'>
      <Label htmlFor='file-upload'>File</Label>
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
            {file ? (
              <>
                <FileText className='w-8 h-8 mb-2 text-primary' />
                <p className='mb-2 text-sm text-gray-500 dark:text-gray-400 font-semibold'>
                  {file.name}
                </p>
                <p className='text-xs text-gray-500 dark:text-gray-400'>
                  {formatBytes(file.size)}
                </p>
              </>
            ) : (
              <>
                <Upload className='w-8 h-8 mb-2 text-gray-500 dark:text-gray-400' />
                <p className='mb-2 text-sm text-gray-500 dark:text-gray-400'>
                  <span className='font-semibold'>Click to upload</span> or drag
                  and drop
                </p>
                <p className='text-xs text-gray-500 dark:text-gray-400'>
                  PDF, DOCX, TXT, MD (MAX. 10MB)
                </p>
              </>
            )}
          </div>
          <input
            id='file-upload'
            type='file'
            className='hidden'
            onChange={handleFileChange}
            accept='.pdf,.docx,.doc,.txt,.md'
          />
        </label>
      </div>
    </div>
  )
}
