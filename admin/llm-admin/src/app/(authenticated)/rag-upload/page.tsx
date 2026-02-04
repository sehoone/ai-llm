'use client'

import { useState } from 'react'
import { Upload, FileText, File as FileIcon, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { ragApi, type DocumentUploadParams } from '@/api/rag'
import { toast } from 'sonner'
import { useRouter } from 'next/navigation'

export default function RagUploadPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  
  const [ragKey, setRagKey] = useState('') 
  const [ragGroup, setRagGroup] = useState('')
  const [ragType, setRagType] = useState<'user_isolated' | 'chatbot_shared' | 'natural_search'>('natural_search')
  const [tags, setTags] = useState('')

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
    }
  }

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
      const fileInput = document.getElementById('file-upload') as HTMLInputElement
      if (fileInput) fileInput.value = ''

    } catch (error: any) {
      console.error(error)
      // Check for specific error message regarding PDF/Docx support
      if (error.response?.data?.detail?.includes('support is not fully configured')) {
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
        <h2 className='text-3xl font-bold tracking-tight'>RAG Document Upload</h2>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card className="md:col-span-2">
            <CardHeader>
                <CardTitle>Upload Document</CardTitle>
            </CardHeader>
            <CardContent>
                <form onSubmit={handleUpload} className="space-y-6">
                    <div className="grid gap-4 md:grid-cols-2">
                        <div className="space-y-2">
                            <Label htmlFor="rag_type">RAG Type</Label>
                            <Select value={ragType} onValueChange={(val: any) => setRagType(val)}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Select type" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="natural_search">Natural Search (Knowledge Base)</SelectItem>
                                    <SelectItem value="user_isolated">User Isolated (Private)</SelectItem>
                                    <SelectItem value="chatbot_shared">Chatbot Shared (Global)</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        
                        <div className="space-y-2">
                            <Label htmlFor="rag_key">RAG Key</Label>
                            <Input 
                                id="rag_key" 
                                placeholder="e.g. project-x-docs"
                                value={ragKey}
                                onChange={e => setRagKey(e.target.value)}
                                required
                            />
                            <p className="text-xs text-muted-foreground">Unique identifier for this collection of documents.</p>
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="rag_group">RAG Group</Label>
                            <Input 
                                id="rag_group" 
                                placeholder="Optional (e.g. engineering)"
                                value={ragGroup}
                                onChange={e => setRagGroup(e.target.value)}
                            />
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="tags">Tags</Label>
                            <Input 
                                id="tags" 
                                placeholder="Comma separated tags"
                                value={tags}
                                onChange={e => setTags(e.target.value)}
                            />
                        </div>
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="file-upload">File</Label>
                        <div className="flex items-center justify-center w-full">
                            <label htmlFor="file-upload" className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed rounded-lg cursor-pointer bg-gray-50 dark:hover:bg-bray-800 dark:bg-gray-700 hover:bg-gray-100 dark:border-gray-600 dark:hover:border-gray-500 dark:hover:bg-gray-600">
                                <div className="flex flex-col items-center justify-center pt-5 pb-6">
                                    {file ? (
                                        <>
                                            <FileText className="w-8 h-8 mb-2 text-primary" />
                                            <p className="mb-2 text-sm text-gray-500 dark:text-gray-400 font-semibold">{file.name}</p>
                                            <p className="text-xs text-gray-500 dark:text-gray-400">
                                                {(file.size / 1024 / 1024).toFixed(2)} MB
                                            </p>
                                        </>
                                    ) : (
                                        <>
                                            <Upload className="w-8 h-8 mb-2 text-gray-500 dark:text-gray-400" />
                                            <p className="mb-2 text-sm text-gray-500 dark:text-gray-400"><span className="font-semibold">Click to upload</span> or drag and drop</p>
                                            <p className="text-xs text-gray-500 dark:text-gray-400">PDF, DOCX, TXT, MD (MAX. 10MB)</p>
                                        </>
                                    )}
                                </div>
                                <input id="file-upload" type="file" className="hidden" onChange={handleFileChange} accept=".pdf,.docx,.doc,.txt,.md" />
                            </label>
                        </div>
                    </div>

                    <div className="flex justify-end gap-2">
                         <Button type="button" variant="outline" onClick={() => setFile(null)}>Reset</Button>
                         <Button type="submit" disabled={loading || !file}>
                            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Upload Document
                        </Button>
                    </div>
                </form>
            </CardContent>
        </Card>
        
        <div className="space-y-4">
             <Card>
                <CardHeader>
                    <CardTitle className="text-sm font-medium">Instructions</CardTitle>
                </CardHeader>
                <CardContent className="text-sm space-y-2 text-muted-foreground">
                    <p>
                        RAG 지식 베이스에 포함할 문서를 여기에 업로드하세요.
                        지원되는 형식은 <strong>PDF</strong>, <strong>Microsoft Word (DOCX)</strong>, 및 일반 텍스트 파일입니다.
                    </p>
                    <p>
                        <strong>RAG Key:</strong> 문서 컬렉션의 주요 식별자입니다. "자연어 검색" 페이지에서 이 키를 사용하여 문서 내를 검색할 수 있습니다.
                    </p>
                    <p>
                        <strong>RAG Type:</strong> User Isolated는 사용자 본인만 문서를 볼 수 있음을 의미합니다. Chatbot Shared는 전역적으로 사용 가능함을 의미합니다(예: 특정 챗봇의 모든 사용자).
                    </p>
                </CardContent>
             </Card>
        </div>
      </div>
    </div>
  )
}
