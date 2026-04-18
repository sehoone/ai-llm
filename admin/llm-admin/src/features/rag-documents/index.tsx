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
import { Input } from '@/components/ui/input'
import { Upload } from 'lucide-react'
import { ragApi, type DocumentResponse, type DocumentDetailResponse } from '@/api/rag'
import { ragGroupApi, type RagGroup, type RagKey } from '@/api/rag-groups'
import { toast } from 'sonner'
import { logger } from '@/lib/logger'
import { UploadForm } from './components/upload-form'
import { DocumentsTable } from './components/documents-table'
import { DocumentViewDialog } from './components/document-view-dialog'
import { TreePanel, type SelectedNode } from './components/tree-panel'

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

  const [selected, setSelected] = useState<SelectedNode>({ type: 'all' })
  const [search, setSearch] = useState('')
  const [ragType, setRagType] = useState('')

  const fetchDocuments = async () => {
    setLoading(true)
    try {
      const docs = await ragApi.getDocuments(undefined, ragType || undefined)
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

  const filteredDocuments = useMemo(() => {
    let docs = documents
    if (selected.type === 'group') docs = docs.filter((d) => d.rag_group === selected.groupName)
    if (selected.type === 'index') docs = docs.filter((d) => d.rag_key === selected.indexKey)
    if (search) docs = docs.filter((d) =>
      d.filename.toLowerCase().includes(search.toLowerCase()) ||
      d.rag_key.includes(search)
    )
    if (ragType) docs = docs.filter((d) => d.rag_type === ragType)
    return docs
  }, [documents, selected, search, ragType])

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

  const uploadDefaults = useMemo(() => {
    if (selected.type === 'group') return { defaultGroup: selected.groupName }
    if (selected.type === 'index') return { defaultGroup: selected.groupName, defaultKey: selected.indexKey }
    return {}
  }, [selected])

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

      <div className='flex border rounded-lg overflow-hidden' style={{ minHeight: '600px' }}>
        {/* Left: Tree */}
        <div className='w-56 shrink-0 border-r bg-muted/20'>
          <TreePanel
            groups={groups}
            keys={keys}
            selected={selected}
            onSelect={setSelected}
            onRefresh={fetchGroupsAndKeys}
          />
        </div>

        {/* Right: Documents */}
        <div className='flex-1 flex flex-col p-4 gap-3 min-w-0'>
          <div className='flex items-center gap-2'>
            <Input
              placeholder='파일명 / RAG Key 검색'
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className='h-8 w-[220px]'
            />
            <select
              className='flex h-8 w-[160px] items-center rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring'
              value={ragType}
              onChange={(e) => setRagType(e.target.value)}
            >
              <option value=''>전체 타입</option>
              <option value='user_isolated'>User Isolated</option>
              <option value='chatbot_shared'>Chatbot Shared</option>
              <option value='natural_search'>Natural Search</option>
            </select>
            <span className='text-sm text-muted-foreground ml-auto'>{filteredDocuments.length}개</span>
          </div>

          <DocumentsTable
            documents={filteredDocuments}
            loading={loading}
            deletingId={deletingId}
            onDelete={handleDelete}
            onView={handleView}
            formatFileSize={formatFileSize}
          />
        </div>
      </div>

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
            {...uploadDefaults}
          />
        </DialogContent>
      </Dialog>
    </div>
  )
}
