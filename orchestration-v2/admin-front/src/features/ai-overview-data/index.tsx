'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import { toast } from 'sonner'
import {
  type ColumnDef,
  type ColumnFiltersState,
  type PaginationState,
  getCoreRowModel,
  useReactTable,
  flexRender,
} from '@tanstack/react-table'
import { Plus, Tag, Trash2, Wand2, RefreshCw, Download } from 'lucide-react'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import {
  aiOverviewApi,
  type AiOverviewDocumentDetail,
  type AiOverviewDocumentSummary,
  type AiOverviewKeyword,
} from '@/api/ai-overview'
import { logger } from '@/lib/logger'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { DataTablePagination, DataTableToolbar } from '@/components/data-table'
import { downloadSampleJson } from './sample-download'
import { DocumentDetailDialog } from './components/document-detail-dialog'
import { DocumentUploadDialog } from './components/document-upload-dialog'
import { KeywordPromptDialog } from './components/keyword-prompt-dialog'
import { KeywordViewDialog } from './components/keyword-view-dialog'

const STATUS_BADGE: Record<string, { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }> = {
  pending:    { label: '대기',    variant: 'secondary' },
  processing: { label: '처리중', variant: 'outline' },
  ready:      { label: '완료',   variant: 'default' },
  error:      { label: '오류',   variant: 'destructive' },
}

export default function AiOverviewData() {
  const [docs, setDocs] = useState<AiOverviewDocumentSummary[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [rowSelection, setRowSelection] = useState({})
  const [bulkDeleting, setBulkDeleting] = useState(false)
  const [generatingId, setGeneratingId] = useState<number | null>(null)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [deleteAllPending, setDeleteAllPending] = useState(false)

  // 서버 사이드 페이지네이션 / 검색 상태
  const [pagination, setPagination] = useState<PaginationState>({ pageIndex: 0, pageSize: 20 })
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])

  // 강제 재조회용 키 (업로드/삭제 후 현재 페이지 새로고침)
  const [refreshKey, setRefreshKey] = useState(0)
  const refresh = useCallback(() => { setRowSelection({}); setRefreshKey((k) => k + 1) }, [])

  const [detailDoc, setDetailDoc] = useState<AiOverviewDocumentDetail | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [detailLoading, setDetailLoading] = useState(false)
  const [promptDialogDoc, setPromptDialogDoc] = useState<AiOverviewDocumentSummary | null>(null)
  const [keywordDialogDoc, setKeywordDialogDoc] = useState<AiOverviewDocumentSummary | null>(null)
  const [keywordDialogData, setKeywordDialogData] = useState<AiOverviewKeyword[]>([])
  const [keywordDialogLoading, setKeywordDialogLoading] = useState(false)

  // ── 서버 조회 ──────────────────────────────────────────────────────────────
  const titleFilter = (columnFilters.find((f) => f.id === 'title')?.value as string) ?? ''

  useEffect(() => {
    let cancelled = false

    // 타이핑 중 불필요한 연속 호출 방지용 짧은 디바운스
    const timer = setTimeout(async () => {
      setLoading(true)
      try {
        const res = await aiOverviewApi.listDocuments(
          pagination.pageIndex * pagination.pageSize,
          pagination.pageSize,
          titleFilter
        )
        if (!cancelled) {
          setDocs(res.items)
          setTotal(res.total)
        }
      } catch (error) {
        if (!cancelled) {
          logger.error(error)
          toast.error('문서 목록을 불러오지 못했습니다')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }, titleFilter ? 250 : 0) // 검색어 있을 때만 디바운스, 페이지 이동은 즉시

    return () => { cancelled = true; clearTimeout(timer) }
  }, [pagination.pageIndex, pagination.pageSize, titleFilter, refreshKey])

  // ── 단건 삭제 ──────────────────────────────────────────────────────────────
  const handleDelete = useCallback(async (doc: AiOverviewDocumentSummary) => {
    if (!confirm(`'${doc.title}' 문서를 삭제하시겠습니까?`)) return
    setDeletingId(doc.id)
    try {
      await aiOverviewApi.deleteDocument(doc.id)
      toast.success('문서가 삭제되었습니다')
      refresh()
    } catch (error) {
      logger.error(error)
      toast.error('문서 삭제에 실패했습니다')
    } finally {
      setDeletingId(null)
    }
  }, [refresh])

  // ── 복수 삭제 ──────────────────────────────────────────────────────────────
  const handleBulkDelete = async (ids: number[]) => {
    if (!ids.length) return
    if (!confirm(`선택한 ${ids.length}개 문서를 삭제하시겠습니까?`)) return
    setBulkDeleting(true)
    try {
      const { deleted } = await aiOverviewApi.batchDeleteDocuments(ids)
      toast.success(`${deleted}개 문서가 삭제되었습니다`)
      refresh()
    } catch (error) {
      logger.error(error)
      toast.error('삭제에 실패했습니다')
    } finally {
      setBulkDeleting(false)
    }
  }

  // ── 키워드 생성 ────────────────────────────────────────────────────────────
  const handleGenerateKeywords = useCallback(async (doc: AiOverviewDocumentSummary, systemPrompt?: string, model?: string) => {
    setPromptDialogDoc(null)
    setGeneratingId(doc.id)
    setDocs((prev) => prev.map((d) => (d.id === doc.id ? { ...d, status: 'processing' } : d)))
    try {
      const result = await aiOverviewApi.generateKeywords(doc.id, systemPrompt, model)
      toast.success(`키워드 ${result.keyword_count}개 생성 완료`)
      setDocs((prev) =>
        prev.map((d) =>
          d.id === doc.id ? { ...d, status: 'ready', keyword_count: result.keyword_count } : d
        )
      )
    } catch (error) {
      logger.error(error)
      toast.error('키워드 생성에 실패했습니다')
      setDocs((prev) => prev.map((d) => (d.id === doc.id ? { ...d, status: 'error' } : d)))
    } finally {
      setGeneratingId(null)
    }
  }, [])

  // ── 키워드 보기 ────────────────────────────────────────────────────────────
  const handleOpenKeywords = useCallback(async (doc: AiOverviewDocumentSummary) => {
    setKeywordDialogDoc(doc)
    setKeywordDialogLoading(true)
    try {
      setKeywordDialogData(await aiOverviewApi.listKeywords(doc.id))
    } catch (error) {
      logger.error(error)
      toast.error('키워드를 불러오지 못했습니다')
    } finally {
      setKeywordDialogLoading(false)
    }
  }, [])

  const handleOpenDetail = useCallback(async (doc: AiOverviewDocumentSummary) => {
    setDetailOpen(true)
    setDetailDoc(null)
    setDetailLoading(true)
    try {
      setDetailDoc(await aiOverviewApi.getDocument(doc.id))
    } catch (error) {
      logger.error(error)
      toast.error('문서를 불러오지 못했습니다')
      setDetailOpen(false)
    } finally {
      setDetailLoading(false)
    }
  }, [])

  const handleDeleteAll = async () => {
    setDeleteAllPending(true)
    try {
      const { deleted } = await aiOverviewApi.deleteAllDocuments()
      toast.success(`${deleted}개 문서가 모두 삭제되었습니다`)
      refresh()
    } catch (error) {
      logger.error(error)
      toast.error('전체 삭제에 실패했습니다')
    } finally {
      setDeleteAllPending(false)
    }
  }

  const handleKeywordsChange = (updated: AiOverviewKeyword[]) => {
    setKeywordDialogData(updated)
    if (keywordDialogDoc) {
      setDocs((prev) =>
        prev.map((d) => (d.id === keywordDialogDoc.id ? { ...d, keyword_count: updated.length } : d))
      )
    }
  }

  // ── 컬럼 정의 ──────────────────────────────────────────────────────────────
  const columns = useMemo<ColumnDef<AiOverviewDocumentSummary>[]>(
    () => [
      {
        id: 'select',
        header: ({ table }) => (
          <Checkbox
            checked={table.getIsAllPageRowsSelected() || (table.getIsSomePageRowsSelected() && 'indeterminate')}
            onCheckedChange={(v) => table.toggleAllPageRowsSelected(!!v)}
            aria-label='전체 선택'
          />
        ),
        cell: ({ row }) => (
          <Checkbox
            checked={row.getIsSelected()}
            onCheckedChange={(v) => row.toggleSelected(!!v)}
            aria-label='행 선택'
          />
        ),
        enableSorting: false,
        enableHiding: false,
        size: 40,
      },
      {
        accessorKey: 'title',
        header: '제목',
        cell: ({ row }) => (
          <button
            type='button'
            className='font-medium line-clamp-1 text-left hover:underline underline-offset-2 cursor-pointer'
            onClick={() => handleOpenDetail(row.original)}
          >
            {row.getValue('title')}
          </button>
        ),
        enableHiding: false,
      },
      {
        accessorKey: 'status',
        header: '상태',
        cell: ({ row }) => {
          const badge = STATUS_BADGE[row.getValue<string>('status')] ?? STATUS_BADGE.pending
          return <Badge variant={badge.variant}>{badge.label}</Badge>
        },
        size: 90,
        enableSorting: false,
      },
      {
        accessorKey: 'keyword_count',
        header: () => <div className='text-center'>키워드</div>,
        cell: ({ row }) => (
          <div className='text-center text-sm text-muted-foreground'>{row.getValue('keyword_count')}</div>
        ),
        size: 80,
      },
      {
        accessorKey: 'created_at',
        header: '등록일',
        cell: ({ row }) => (
          <span className='text-sm text-muted-foreground'>
            {new Date(row.getValue<string>('created_at')).toLocaleDateString('ko-KR')}
          </span>
        ),
        size: 110,
      },
      {
        id: 'actions',
        header: () => <div className='text-right'>액션</div>,
        cell: ({ row }) => {
          const doc = row.original
          const isGenerating = generatingId === doc.id
          const isDeleting = deletingId === doc.id
          return (
            <div className='flex justify-end gap-1'>
              <Button variant='ghost' size='sm' className='h-7 px-2 text-xs'
                onClick={() => handleOpenKeywords(doc)} disabled={isGenerating || isDeleting}>
                <Tag className='h-3 w-3 mr-1' />키워드
              </Button>
              <Button variant='ghost' size='sm' className='h-7 px-2 text-xs'
                onClick={() => setPromptDialogDoc(doc)} disabled={isGenerating || isDeleting}>
                <Wand2 className={`h-3 w-3 mr-1 ${isGenerating ? 'animate-spin' : ''}`} />
                {isGenerating ? '생성중' : '키워드 생성'}
              </Button>
              <Button variant='ghost' size='sm'
                className='h-7 px-2 text-xs text-destructive hover:text-destructive'
                onClick={() => handleDelete(doc)} disabled={isGenerating || isDeleting || bulkDeleting}>
                <Trash2 className='h-3 w-3' />
              </Button>
            </div>
          )
        },
        enableSorting: false,
        enableHiding: false,
      },
    ],
    [generatingId, deletingId, bulkDeleting, handleDelete, handleGenerateKeywords, handleOpenKeywords, handleOpenDetail]
  )

  // ── TanStack Table (서버 사이드 페이지네이션/필터링) ───────────────────────
  const table = useReactTable({
    data: docs,
    columns,
    state: { pagination, rowSelection, columnFilters },
    manualPagination: true,
    manualFiltering: true,
    pageCount: Math.ceil(total / pagination.pageSize),
    onPaginationChange: setPagination,
    onColumnFiltersChange: (updater) => {
      setColumnFilters(updater)
      // 검색어 변경 시 첫 페이지로 이동
      setPagination((prev) => ({ ...prev, pageIndex: 0 }))
    },
    onRowSelectionChange: setRowSelection,
    getCoreRowModel: getCoreRowModel(),
    enableRowSelection: true,
  })

  const selectedRows = table.getSelectedRowModel().rows
  const selectedIds = selectedRows.map((r) => r.original.id)

  return (
    <div className='flex flex-col gap-4 p-4 md:p-8'>
      {/* 헤더 */}
      <div className='flex items-center justify-between'>
        <div>
          <h2 className='text-3xl font-bold tracking-tight'>AI Overview Data</h2>
          <p className='text-muted-foreground mt-1'>
            AI Overview 검색에 사용될 사내 데이터를 관리합니다. 총 {total}개
          </p>
        </div>
        <div className='flex gap-2'>
          <Button variant='outline' size='icon' onClick={refresh} disabled={loading}>
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
          <Button variant='outline' onClick={downloadSampleJson}>
            <Download className='mr-2 h-4 w-4' />
            샘플 다운로드
          </Button>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant='outline' className='text-destructive hover:text-destructive' disabled={deleteAllPending || total === 0}>
                <Trash2 className='mr-2 h-4 w-4' />
                {deleteAllPending ? '삭제 중...' : '전체 삭제'}
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>전체 삭제</AlertDialogTitle>
                <AlertDialogDescription>
                  등록된 문서 {total}개와 키워드 데이터가 모두 삭제됩니다.{' '}
                  이 작업은 되돌릴 수 없습니다.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>취소</AlertDialogCancel>
                <AlertDialogAction
                  className='bg-destructive text-destructive-foreground hover:bg-destructive/90'
                  onClick={handleDeleteAll}
                >
                  전체 삭제
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
          <Button onClick={() => setUploadOpen(true)}>
            <Plus className='mr-2 h-4 w-4' />
            문서 등록
          </Button>
        </div>
      </div>

      {/* 검색 툴바 */}
      <DataTableToolbar table={table} searchKey='title' searchPlaceholder='제목으로 검색...' />

      {/* 선택 액션 바 */}
      {selectedIds.length > 0 && (
        <div className='flex items-center gap-3 rounded-lg border bg-muted/50 px-4 py-2'>
          <span className='text-sm font-medium'>{selectedIds.length}개 선택됨</span>
          <Button variant='destructive' size='sm'
            onClick={() => handleBulkDelete(selectedIds)} disabled={bulkDeleting}>
            <Trash2 className='mr-1.5 h-3.5 w-3.5' />
            {bulkDeleting ? '삭제 중...' : '선택 삭제'}
          </Button>
          <Button variant='ghost' size='sm'
            onClick={() => setRowSelection({})} disabled={bulkDeleting}>
            선택 해제
          </Button>
        </div>
      )}

      {/* 테이블 */}
      <div className='rounded-md border'>
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((hg) => (
              <TableRow key={hg.id}>
                {hg.headers.map((header) => (
                  <TableHead key={header.id} style={{ width: header.getSize() }}>
                    {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={columns.length} className='text-center py-10 text-muted-foreground'>
                  불러오는 중...
                </TableCell>
              </TableRow>
            ) : table.getRowModel().rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={columns.length} className='text-center py-10 text-muted-foreground'>
                  {titleFilter ? `'${titleFilter}' 검색 결과가 없습니다` : '등록된 문서가 없습니다'}
                </TableCell>
              </TableRow>
            ) : (
              table.getRowModel().rows.map((row) => (
                <TableRow key={row.id} data-state={row.getIsSelected() ? 'selected' : undefined}>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* 페이지네이션 */}
      <DataTablePagination table={table} />

      {/* 다이얼로그 */}
      <DocumentDetailDialog
        open={detailOpen}
        doc={detailDoc}
        loading={detailLoading}
        onOpenChange={setDetailOpen}
      />

      <DocumentUploadDialog open={uploadOpen} onOpenChange={setUploadOpen} onSuccess={refresh} />

      <KeywordPromptDialog
        open={!!promptDialogDoc}
        doc={promptDialogDoc}
        onOpenChange={(open) => { if (!open) setPromptDialogDoc(null) }}
        onGenerate={handleGenerateKeywords}
        isGenerating={promptDialogDoc !== null && generatingId === promptDialogDoc.id}
      />

      {keywordDialogDoc && (
        <KeywordViewDialog
          open={!!keywordDialogDoc}
          onOpenChange={(open) => { if (!open) setKeywordDialogDoc(null) }}
          docId={keywordDialogDoc.id}
          docTitle={keywordDialogDoc.title}
          keywords={keywordDialogLoading ? [] : keywordDialogData}
          onKeywordsChange={handleKeywordsChange}
        />
      )}
    </div>
  )
}
