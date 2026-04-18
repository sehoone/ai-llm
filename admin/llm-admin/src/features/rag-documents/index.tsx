'use client'

import { useState, useEffect, useMemo } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Upload } from 'lucide-react'
import { ragApi, type DocumentResponse, type DocumentDetailResponse } from '@/api/rag'
import { ragGroupApi, type RagGroup, type RagKey } from '@/api/rag-groups'
import { toast } from 'sonner'
import { logger } from '@/lib/logger'
import { UploadForm } from './components/upload-form'
import { DocumentsFilter } from './components/documents-filter'
import { DocumentsTable } from './components/documents-table'
import { DocumentViewDialog } from './components/document-view-dialog'
import { GroupsTab } from './components/groups-tab'
import { KeysTab } from './components/keys-tab'

export default function RagDocuments() {
  const [documents, setDocuments] = useState<DocumentResponse[]>([])
  const [groups, setGroups] = useState<RagGroup[]>([])
  const [keys, setKeys] = useState<RagKey[]>([])
  const [loading, setLoading] = useState(true)
  const [deletingId, setDeletingId] = useState<number | null>(null)

  const [viewDoc, setViewDoc] = useState<DocumentDetailResponse | null>(null)
  const [viewLoading, setViewLoading] = useState(false)
  const [isOpen, setIsOpen] = useState(false)
  const [isUploadOpen, setIsUploadOpen] = useState(false)

  const [ragKey, setRagKey] = useState('')
  const [ragGroup, setRagGroup] = useState('')
  const [ragType, setRagType] = useState<string>('')

  const availableGroups = useMemo(
    () => [...new Set(documents.map((d) => d.rag_group))].sort(),
    [documents]
  )

  const fetchDocuments = async () => {
    setLoading(true)
    try {
      const docs = await ragApi.getDocuments(ragKey || undefined, ragType || undefined)
      setDocuments(docs)
    } catch (error) {
      logger.error(error)
      toast.error('문서 목록을 불러오지 못했습니다')
    } finally {
      setLoading(false)
    }
  }

  const fetchGroupsAndKeys = async () => {
    try {
      const [g, k] = await Promise.all([ragGroupApi.listGroups(), ragGroupApi.listKeys()])
      setGroups(g)
      setKeys(k)
    } catch (error) {
      logger.error(error)
    }
  }

  useEffect(() => {
    fetchDocuments()
    fetchGroupsAndKeys()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const filteredDocuments = useMemo(
    () => (ragGroup ? documents.filter((d) => d.rag_group === ragGroup) : documents),
    [documents, ragGroup]
  )

  const handleDelete = async (id: number) => {
    if (!confirm('이 문서를 삭제하시겠습니까?')) return
    setDeletingId(id)
    try {
      await ragApi.deleteDocument(id)
      toast.success('문서가 삭제되었습니다')
      setDocuments((prev) => prev.filter((doc) => doc.id !== id))
    } catch (error) {
      logger.error(error)
      toast.error('문서 삭제에 실패했습니다')
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
      toast.error('문서 내용을 불러오지 못했습니다')
      setIsOpen(false)
    } finally {
      setViewLoading(false)
    }
  }

  const handleUploadSuccess = () => {
    setIsUploadOpen(false)
    fetchDocuments()
    fetchGroupsAndKeys()
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  return (
    <div className='flex flex-col gap-4 p-4 md:p-8'>
      <div className='flex items-center justify-between'>
        <div>
          <h2 className='text-3xl font-bold tracking-tight'>RAG Documents</h2>
          <p className='text-muted-foreground'>업로드된 문서와 지식 베이스를 관리합니다.</p>
        </div>
        <Button onClick={() => setIsUploadOpen(true)}>
          <Upload className='mr-2 h-4 w-4' />
          문서 업로드
        </Button>
      </div>

      <Tabs defaultValue='documents'>
        <TabsList>
          <TabsTrigger value='documents'>문서</TabsTrigger>
          <TabsTrigger value='groups'>카테고리 관리</TabsTrigger>
          <TabsTrigger value='keys'>컬렉션 관리</TabsTrigger>
        </TabsList>

        <TabsContent value='documents' className='mt-4'>
          <DocumentsFilter
            ragKey={ragKey}
            setRagKey={setRagKey}
            ragGroup={ragGroup}
            setRagGroup={setRagGroup}
            ragType={ragType}
            setRagType={setRagType}
            onApplyFilters={fetchDocuments}
            availableGroups={availableGroups}
          />
          <div className='mt-4'>
            <DocumentsTable
              documents={filteredDocuments}
              loading={loading}
              deletingId={deletingId}
              onDelete={handleDelete}
              onView={handleView}
              formatFileSize={formatFileSize}
            />
          </div>
        </TabsContent>

        <TabsContent value='groups' className='mt-4'>
          <GroupsTab groups={groups} onRefresh={fetchGroupsAndKeys} />
        </TabsContent>

        <TabsContent value='keys' className='mt-4'>
          <KeysTab keys={keys} groups={groups} onRefresh={fetchGroupsAndKeys} />
        </TabsContent>
      </Tabs>

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

      <Dialog open={isUploadOpen} onOpenChange={setIsUploadOpen}>
        <DialogContent className='max-w-4xl'>
          <DialogHeader>
            <DialogTitle>문서 업로드</DialogTitle>
            <DialogDescription>RAG 지식 베이스에 새 문서를 업로드합니다.</DialogDescription>
          </DialogHeader>
          <UploadForm
            onSuccess={handleUploadSuccess}
            groups={groups}
            keys={keys}
          />
        </DialogContent>
      </Dialog>
    </div>
  )
}
