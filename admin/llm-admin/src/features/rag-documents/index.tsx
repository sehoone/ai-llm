'use client'

import { useState, useEffect } from 'react'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Upload } from 'lucide-react'
import { ragApi, type DocumentResponse, type DocumentDetailResponse } from '@/api/rag'
import { toast } from 'sonner'
import { logger } from '@/lib/logger'
import { UploadForm } from '@/features/rag-upload/components/upload-form'
import { DocumentsFilter } from './components/documents-filter'
import { DocumentsTable } from './components/documents-table'
import { DocumentViewDialog } from './components/document-view-dialog'

export default function RagDocuments() {
  const [documents, setDocuments] = useState<DocumentResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  
  // View Dialog State
  const [viewDoc, setViewDoc] = useState<DocumentDetailResponse | null>(null)
  const [viewLoading, setViewLoading] = useState(false)
  const [isOpen, setIsOpen] = useState(false)

  // Upload Dialog State
  const [isUploadOpen, setIsUploadOpen] = useState(false)

  // Filters
  const [ragKey, setRagKey] = useState('')
  const [ragType, setRagType] = useState<string>('')

  const fetchDocuments = async () => {
    setLoading(true)
    try {
      const docs = await ragApi.getDocuments(ragKey || undefined, ragType || undefined)
      setDocuments(docs)
    } catch (error) {
      logger.error(error)
      toast.error('Failed to load documents')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDocuments()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this document?')) return

    setDeletingId(id)
    try {
      await ragApi.deleteDocument(id)
      toast.success('Document deleted successfully')
      setDocuments(prev => prev.filter(doc => doc.id !== id))
    } catch (error) {
      logger.error(error)
      toast.error('Failed to delete document')
    } finally {
      setDeletingId(null)
    }
  }

  const handleView = async (doc: DocumentResponse) => {
    setViewLoading(true)
    setIsOpen(true)
    try {
      const detail = await ragApi.getDocument(doc.id)
      setViewDoc(detail)
    } catch (error) {
      logger.error(error)
      toast.error('Failed to load document content')
      setIsOpen(false)
    } finally {
      setViewLoading(false)
    }
  }

  const handleUploadSuccess = () => {
    setIsUploadOpen(false)
    fetchDocuments()
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  return (
    <div className="flex flex-col gap-4 p-4 md:p-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">RAG Documents</h2>
          <p className="text-muted-foreground">
            Manage your uploaded documents and knowledge base.
          </p>
        </div>
        <div className="flex gap-2">
            <Button onClick={() => setIsUploadOpen(true)}>
                <Upload className="mr-2 h-4 w-4" />
                Upload Document
            </Button>
            <Button onClick={fetchDocuments} variant="outline" size="sm">
            Refresh
            </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
           <CardTitle>Documents</CardTitle>
           <CardDescription>
             List of all documents uploaded to your RAG knowledge base.
           </CardDescription>
           
           <DocumentsFilter 
                ragKey={ragKey}
                setRagKey={setRagKey}
                ragType={ragType}
                setRagType={setRagType}
                onApplyFilters={fetchDocuments}
           />
        </CardHeader>
        <CardContent>
          <DocumentsTable 
            documents={documents}
            loading={loading}
            deletingId={deletingId}
            onDelete={handleDelete}
            onView={handleView}
            formatFileSize={formatFileSize}
          />
        </CardContent>
      </Card>

      <DocumentViewDialog
        isOpen={isOpen}
        onOpenChange={(open) => {
            setIsOpen(open)
            if (!open) setViewDoc(null)
        }}
        viewDoc={viewDoc}
        viewLoading={viewLoading}
        formatFileSize={formatFileSize}
      />

      {/* Upload Dialog */}
      <Dialog open={isUploadOpen} onOpenChange={setIsUploadOpen}>
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle>Upload Document</DialogTitle>
            <DialogDescription>
              Upload a new document to your RAG knowledge base.
            </DialogDescription>
          </DialogHeader>
          <UploadForm onSuccess={handleUploadSuccess} />
        </DialogContent>
      </Dialog>
    </div>
  )
}
