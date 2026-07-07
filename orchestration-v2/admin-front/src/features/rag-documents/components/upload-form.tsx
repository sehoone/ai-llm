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
  defaultGroup?: string
  defaultKey?: string
  /** @deprecated use groups/keys */
  availableKeys?: string[]
  /** @deprecated use groups/keys */
  availableGroups?: string[]
}

export function UploadForm({ onSuccess, groups = [], keys = [], defaultGroup = '', defaultKey = '' }: UploadFormProps) {
  const [loading, setLoading] = useState(false)
  const [files, setFiles] = useState<File[]>([])
  const [uploadProgress, setUploadProgress] = useState({ current: 0, total: 0 })

  const [ragKey, setRagKey] = useState(defaultKey)
  const [ragGroup, setRagGroup] = useState(defaultGroup)
  const [ragType, setRagType] = useState<'user_isolated' | 'chatbot_shared' | 'natural_search'>('natural_search')
  const [tags, setTags] = useState('')

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault()
    if (files.length === 0 || !ragKey) {
      toast.error('파일과 RAG Key를 선택해주세요')
      return
    }

    setLoading(true)
    setUploadProgress({ current: 0, total: files.length })

    let successCount = 0
    const failedNames: string[] = []

    for (let i = 0; i < files.length; i++) {
      setUploadProgress({ current: i + 1, total: files.length })
      try {
        const params: DocumentUploadParams = {
          file: files[i],
          rag_key: ragKey,
          rag_group: ragGroup || 'default',
          rag_type: ragType,
          tags,
        }
        await ragApi.uploadDocument(params)
        successCount++
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      } catch (error: any) {
        logger.error(error)
        const detail = error.response?.data?.detail
        if (detail?.includes('support is not fully configured')) {
          toast.error(detail)
        } else {
          failedNames.push(files[i].name)
        }
      }
    }

    setLoading(false)
    setUploadProgress({ current: 0, total: 0 })

    if (successCount > 0) {
      toast.success(`${successCount}개 문서가 업로드되었습니다`)
      setFiles([])
      setTags('')
      onSuccess?.()
    }
    if (failedNames.length > 0) {
      toast.error(`${failedNames.length}개 파일 업로드 실패: ${failedNames.join(', ')}`)
    }
  }

  const uploadLabel = loading
    ? `Uploading ${uploadProgress.current}/${uploadProgress.total}...`
    : files.length > 1
      ? `Upload ${files.length} Documents`
      : 'Upload Document'

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

      <FileDropzone files={files} setFiles={setFiles} />

      <div className='flex justify-end gap-2'>
        <Button type='button' variant='outline' onClick={() => setFiles([])} disabled={loading}>
          Reset
        </Button>
        <Button type='submit' disabled={loading || files.length === 0 || !ragKey}>
          {loading && <Loader2 className='mr-2 h-4 w-4 animate-spin' />}
          {uploadLabel}
        </Button>
      </div>
    </form>
  )
}
