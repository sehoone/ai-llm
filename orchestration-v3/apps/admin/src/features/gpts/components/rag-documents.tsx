'use client'

import { useEffect, useState, useRef } from 'react'
import { FileUp, FileText } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { ragApi, type DocumentResponse } from '@/api/rag'
import { toast } from 'sonner'
import { logger } from '@/lib/logger'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'

interface RagDocumentsProps {
  ragKey: string
  ragType?: string
}

export function RagDocuments({ ragKey, ragType = 'chatbot_shared' }: RagDocumentsProps) {
  const [documents, setDocuments] = useState<DocumentResponse[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const loadDocuments = async () => {
      setIsLoading(true)
      try {
        const data = await ragApi.getDocuments(ragKey, ragType)
        setDocuments(data)
      } catch (error) {
        logger.error('Failed to load documents', error)
        toast.error('Failed to load documents')
      } finally {
        setIsLoading(false)
      }
    }

    if (ragKey) {
      loadDocuments()
    }
  }, [ragKey, ragType])

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0]
      await uploadFile(file)
      // Reset input
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const uploadFile = async (file: File) => {
    setIsUploading(true)
    try {
      const result = await ragApi.uploadDocument({
        file,
        rag_key: ragKey,
        rag_group: 'custom_gpt',
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        rag_type: ragType as any,
        tags: 'custom_gpt_knowledge',
      })
      toast.success(`Uploaded ${file.name}`)
      setDocuments(prev => [result, ...prev])
    } catch (error) {
      logger.error('Failed to upload document', error)
      toast.error('Failed to upload document')
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Documents</CardTitle>
        <CardDescription>
          Files uploaded here are processed and indexed for retrieval.
        </CardDescription>
      </CardHeader>
      <CardContent>
         <div className="flex flex-col gap-4">
            <div className="flex items-center gap-2">
                <Button 
                    disabled={isUploading} 
                    onClick={() => fileInputRef.current?.click()}
                    variant="outline"
                    className="w-full sm:w-auto"
                >
                    <FileUp className="mr-2 h-4 w-4" />
                    {isUploading ? 'Uploading...' : 'Upload Document'}
                </Button>
                <input
                    type="file"
                    ref={fileInputRef}
                    className="hidden"
                    onChange={handleFileSelect}
                    accept=".pdf,.txt,.md,.docx,.doc"
                />
            </div>

            <Separator />

            <div className="min-h-[100px]">
                {isLoading ? (
                    <div className="text-sm text-muted-foreground p-4 text-center">Loading documents...</div>
                ) : documents.length === 0 ? (
                    <div className="text-sm text-muted-foreground p-4 text-center border border-dashed rounded-md">
                        No documents uploaded yet.
                    </div>
                ) : (
                    <ScrollArea className="h-[300px] w-full rounded-md border p-4">
                        <div className="flex flex-col gap-2">
                            {documents.map((doc) => (
                                <div key={doc.id} className="flex items-center justify-between p-2 rounded-md hover:bg-muted/50 border">
                                    <div className="flex items-center gap-3 overflow-hidden">
                                        <div className="bg-primary/10 p-2 rounded">
                                            <FileText className="h-4 w-4 text-primary" />
                                        </div>
                                        <div className="flex flex-col overflow-hidden">
                                            <span className="text-sm font-medium truncate">{doc.filename}</span>
                                            <span className="text-xs text-muted-foreground">
                                                {(doc.size / 1024).toFixed(1)} KB • {new Date(doc.created_at).toLocaleDateString()}
                                            </span>
                                        </div>
                                    </div>
                                    {/* Delete not implemented in backend yet */}
                                    {/* <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-destructive">
                                        <Trash2 className="h-4 w-4" />
                                    </Button> */}
                                </div>
                            ))}
                        </div>
                    </ScrollArea>
                )}
            </div>
         </div>
      </CardContent>
    </Card>
  )
}
