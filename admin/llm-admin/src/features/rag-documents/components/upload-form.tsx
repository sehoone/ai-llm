'use client'

import { useState } from 'react'
import { Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ragApi, type DocumentUploadParams } from '@/api/rag'
import type { RagGroup, RagKey } from '@/api/rag-groups'
import { toast } from 'sonner'
import { logger } from '@/lib/logger'
import { UploadConfiguration } from './upload-configuration'
import { FileDropzone } from './file-dropzone'

interface UploadFormProps {
  onSuccess?: () => void
  groups?: RagGroup[]
  keys?: RagKey[]
  /** @deprecated use groups/keys */
  availableKeys?: string[]
  /** @deprecated use groups/keys */
  availableGroups?: string[]
}

export function UploadForm({ onSuccess, groups = [], keys = [] }: UploadFormProps) {
  const [loading, setLoading] = useState(false)
  const [file, setFile] = useState<File | null>(null)

  const [ragKey, setRagKey] = useState('')
  const [ragGroup, setRagGroup] = useState('')
  const [ragType, setRagType] = useState<'user_isolated' | 'chatbot_shared' | 'natural_search'>('natural_search')
  const [tags, setTags] = useState('')

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file || !ragKey) {
      toast.error('파일과 RAG Key를 선택해주세요')
      return
    }

    setLoading(true)
    try {
      const params: DocumentUploadParams = {
        file,
        rag_key: ragKey,
        rag_group: ragGroup || 'default',
        rag_type: ragType,
        tags,
      }
      await ragApi.uploadDocument(params)
      toast.success('문서가 업로드되었습니다')
      setFile(null)
      setTags('')
      const fileInput = document.getElementById('file-upload') as HTMLInputElement
      if (fileInput) fileInput.value = ''
      onSuccess?.()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (error: any) {
      logger.error(error)
      if (error.response?.data?.detail?.includes('support is not fully configured')) {
        toast.error(error.response.data.detail)
      } else {
        toast.error('업로드에 실패했습니다. 다시 시도해주세요.')
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
        groups={groups}
        keys={keys}
      />

      <FileDropzone file={file} setFile={setFile} />

      <div className='flex justify-end gap-2'>
        <Button type='button' variant='outline' onClick={() => setFile(null)} disabled={loading}>
          Reset
        </Button>
        <Button type='submit' disabled={loading || !file || !ragKey}>
          {loading && <Loader2 className='mr-2 h-4 w-4 animate-spin' />}
          Upload Document
        </Button>
      </div>
    </form>
  )
}
