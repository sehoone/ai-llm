'use client'

import { useEffect, useState } from 'react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Loader2, Trash2, FileText, Calendar, Eye } from 'lucide-react'
import { ragApi, type DocumentResponse, type DocumentDetailResponse } from '@/api/rag'
import { toast } from 'sonner'
import { format } from 'date-fns'
import { logger } from '@/lib/logger'

export default function RagDocumentsPage() {
  const [documents, setDocuments] = useState<DocumentResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  
  // View Dialog State
  const [viewDoc, setViewDoc] = useState<DocumentDetailResponse | null>(null)
  const [viewLoading, setViewLoading] = useState(false)
  const [isOpen, setIsOpen] = useState(false)

  // Filters
  const [ragKey, setRagKey] = useState('')
  const [ragType, setRagType] = useState<string>('') // Optional: filter by type

  const fetchDocuments = async () => {
    setLoading(true)
    try {
      // Pass filters if they have values, otherwise undefined
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
  }, []) // Initial load

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this document?')) return

    setDeletingId(id)
    try {
      await ragApi.deleteDocument(id)
      toast.success('Document deleted successfully')
      // Remove from list immediately
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
      setIsOpen(false) // Close if failed
    } finally {
      setViewLoading(false)
    }
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
        <Button onClick={fetchDocuments} variant="outline" size="sm">
          Refresh
        </Button>
      </div>

      <Card>
        <CardHeader>
           <CardTitle>Documents</CardTitle>
           <CardDescription>
             List of all documents uploaded to your RAG knowledge base.
           </CardDescription>
           <div className="flex gap-4 mt-4">
             <div className="w-[200px]">
               <Input 
                 placeholder="Filter by RAG Key" 
                 value={ragKey}
                 onChange={(e) => setRagKey(e.target.value)}
                 className="h-8"
               />
             </div>
             <div className="w-[200px]">
                <select
                    className="flex h-8 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                    value={ragType}
                    onChange={(e) => setRagType(e.target.value)}
                >
                    <option value="">All Types</option>
                    <option value="user_isolated">User Isolated</option>
                    <option value="chatbot_shared">Chatbot Shared</option>
                    <option value="natural_search">Natural Search</option>
                </select>
             </div>
             <Button size="sm" onClick={fetchDocuments}>Apply Filters</Button>
           </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex h-40 items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : documents.length === 0 ? (
            <div className="flex h-40 flex-col items-center justify-center text-muted-foreground">
              <FileText className="mb-2 h-10 w-10 opacity-20" />
              <p>No documents found</p>
            </div>
          ) : (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Filename</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Key</TableHead>
                    <TableHead>Group</TableHead>
                    <TableHead>Size</TableHead>
                    <TableHead>Created At</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {documents.map((doc) => (
                    <TableRow key={doc.id}>
                      <TableCell className="font-medium">
                        <div className="flex items-center gap-2">
                           <FileText className="h-4 w-4 text-blue-500" />
                           {doc.filename}
                        </div>
                      </TableCell>
                      <TableCell><Badge variant="outline">{doc.rag_type}</Badge></TableCell>
                      <TableCell>{doc.rag_key}</TableCell>
                      <TableCell>{doc.rag_group}</TableCell>
                      <TableCell>{formatFileSize(doc.size)}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2 text-muted-foreground">
                          <Calendar className="h-3 w-3" />
                          {doc.created_at ? format(new Date(doc.created_at), 'yyyy-MM-dd HH:mm') : '-'}
                        </div>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleView(doc)}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDelete(doc.id)}
                          disabled={deletingId === doc.id}
                        >
                          {deletingId === doc.id ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Trash2 className="h-4 w-4 text-destructive" />
                          )}
                        </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={isOpen} onOpenChange={(open) => {
        setIsOpen(open)
        if (!open) setViewDoc(null)
      }}>
        <DialogContent className="max-w-3xl h-[80vh] flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
               <FileText className="h-5 w-5 text-blue-500" />
               {viewDoc ? viewDoc.filename : 'Loading...'}
            </DialogTitle>
            <DialogDescription>
              {viewDoc ? `Size: ${formatFileSize(viewDoc.size)}` : 'Fetching content...'}
            </DialogDescription>
          </DialogHeader>
          <div className="flex-1 overflow-hidden p-4 border rounded-md bg-muted/30">
             {viewLoading ? (
                 <div className="flex h-full items-center justify-center">
                    <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                 </div>
             ) : (
                <ScrollArea className="h-full w-full">
                    <pre className="text-sm whitespace-pre-wrap font-mono p-2">
                        {viewDoc?.content || 'No content available'}
                    </pre>
                </ScrollArea>
             )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
