'use client'

import { useState } from 'react'
import { Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ragApi, type DocumentUploadParams } from '@/api/rag'
import { toast } from 'sonner'
import { logger } from '@/lib/logger'
import { UploadConfiguration } from './components/upload-configuration'
import { FileDropzone } from './components/file-dropzone'
import { UploadInstructions } from './components/upload-instructions'

export default function RagUpload() {
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

      // Reset form (optional)
      setFile(null)
      // setRagKey('') // Keep key for consecutive uploads
      setTags('')

      // Reset file input value
      const fileInput = document.getElementById(
        'file-upload'
      ) as HTMLInputElement
      if (fileInput) fileInput.value = ''
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
    <div className='flex flex-col gap-4 p-4 md:p-8'>
      <div className='flex items-center justify-between space-y-2'>
        <h2 className='text-3xl font-bold tracking-tight'>
          RAG Document Upload
        </h2>
      </div>

      <div className='grid gap-4 md:grid-cols-2 lg:grid-cols-3'>
        <Card className='md:col-span-2'>
          <CardHeader>
            <CardTitle>Upload Document</CardTitle>
          </CardHeader>
          <CardContent>
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
                >
                  Reset
                </Button>
                <Button type='submit' disabled={loading || !file}>
                  {loading && (
                    <Loader2 className='mr-2 h-4 w-4 animate-spin' />
                  )}
                  Upload Document
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        <div className='space-y-4'>
          <UploadInstructions />
        </div>
      </div>
    </div>
  )
}
