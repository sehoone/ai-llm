'use client'

import { useState } from 'react'
import { Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ragApi, type DocumentUploadParams } from '@/api/rag'
import { toast } from 'sonner'
import { logger } from '@/lib/logger'
import { UploadConfiguration } from './upload-configuration'
import { FileDropzone } from './file-dropzone'

interface UploadFormProps {
  onSuccess?: () => void
}

export function UploadForm({ onSuccess }: UploadFormProps) {
  const [loading, setLoading] = useState(false)
  const [file, setFile] = useState<File | null>(null)

  const [ragKey, setRagKey] = useState('')
  const [ragGroup, setRagGroup] = useState('')
  const [ragType, setRagType] = useState<
    'user_isolated' | 'chatbot_shared' | 'natural_search'
  >('natural_search')
  const [tags, setTags] = useState('')

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file || !ragKey) {
      toast.error('File and RAG Key are required')
      return
    }

    setLoading(true)

    try {
      const params: DocumentUploadParams = {
        file: file,
        rag_key: ragKey,
        rag_group: ragGroup || 'default', // Provide default if empty
        rag_type: ragType,
        tags: tags,
      }

      await ragApi.uploadDocument(params)

      toast.success('Document uploaded successfully')

      // Reset form
      setFile(null)
      // setRagKey('') // Keep key for consecutive uploads? Maybe reset for modal.
      // Let's keep it for now as user might batch upload.
      setTags('')

      // Reset file input value
      const fileInput = document.getElementById(
        'file-upload'
      ) as HTMLInputElement
      if (fileInput) fileInput.value = ''

      if (onSuccess) {
        onSuccess()
      }
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (error: any) {
      logger.error(error)
      // Check for specific error message regarding PDF/Docx support
      if (
        error.response?.data?.detail?.includes('support is not fully configured')
      ) {
        toast.error(error.response.data.detail)
      } else {
        toast.error('Upload failed. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleUpload} className='space-y-6'>
      <UploadConfiguration
        ragType={ragType}
        setRagType={setRagType}
        ragKey={ragKey}
        setRagKey={setRagKey}
        ragGroup={ragGroup}
        setRagGroup={setRagGroup}
        tags={tags}
        setTags={setTags}
      />

      <FileDropzone file={file} setFile={setFile} />

      <div className='flex justify-end gap-2'>
        <Button
          type='button'
          variant='outline'
          onClick={() => setFile(null)}
          disabled={loading}
        >
          Reset
        </Button>
        <Button type='submit' disabled={loading || !file}>
          {loading && <Loader2 className='mr-2 h-4 w-4 animate-spin' />}
          Upload Document
        </Button>
      </div>
    </form>
  )
}
