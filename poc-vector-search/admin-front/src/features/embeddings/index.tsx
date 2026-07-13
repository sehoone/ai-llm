'use client'

import { useRef, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  Trash2, Plus, Loader2, Upload, FileJson,
  CheckCircle2, XCircle, Clock, Ban,
} from 'lucide-react'
import { createEmbedding, deleteEmbedding, listEmbeddings } from '@/api/embeddings'
import { logger } from '@/lib/logger'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Form, FormControl, FormField, FormItem, FormLabel, FormMessage,
} from '@/components/ui/form'
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader,
  AlertDialogTitle, AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Header } from '@/components/layout/header'
import { Main } from '@/components/layout/main'

// ── 타입 ────────────────────────────────────────────────────

type ItemStatus = 'pending' | 'processing' | 'success' | 'error' | 'cancelled'

interface ProgressItem {
  id: string | number
  title: string
  desc: string
  status: ItemStatus
  documentId?: number
  error?: string
}

// ── 스키마 ──────────────────────────────────────────────────

const singleSchema = z.object({
  title: z.string().min(1, '제목을 입력하세요').max(500),
  content: z.string().min(1, '내용을 입력하세요'),
})
type SingleValues = z.infer<typeof singleSchema>

const jsonItemSchema = z.object({
  id: z.union([z.string(), z.number()]),
  title: z.string().min(1),
  desc: z.string().min(1),
})
const jsonFileSchema = z.array(jsonItemSchema).min(1, '항목이 1건 이상이어야 합니다.')

// ── 상태 아이콘 ──────────────────────────────────────────────

function StatusIcon({ status }: { status: ItemStatus }) {
  if (status === 'pending')    return <Clock     className='h-4 w-4 text-muted-foreground' />
  if (status === 'processing') return <Loader2   className='h-4 w-4 animate-spin text-blue-500' />
  if (status === 'success')    return <CheckCircle2 className='h-4 w-4 text-green-500' />
  if (status === 'error')      return <XCircle   className='h-4 w-4 text-destructive' />
  if (status === 'cancelled')  return <Ban       className='h-4 w-4 text-muted-foreground' />
  return null
}

function rowBg(status: ItemStatus) {
  if (status === 'processing') return 'bg-blue-50 dark:bg-blue-950/20'
  if (status === 'success')    return 'bg-green-50 dark:bg-green-950/20'
  if (status === 'error')      return 'bg-red-50 dark:bg-red-950/20'
  return ''
}

// ── 메인 컴포넌트 ────────────────────────────────────────────

export function EmbeddingsFeature() {
  const queryClient = useQueryClient()
  const [deletingId, setDeletingId] = useState<number | null>(null)

  // 단건 폼
  const form = useForm<SingleValues>({
    resolver: zodResolver(singleSchema),
    defaultValues: { title: '', content: '' },
  })

  // 다건 업로드 상태
  const fileInputRef  = useRef<HTMLInputElement>(null)
  const cancelledRef  = useRef(false)
  const [fileName,       setFileName]       = useState<string | null>(null)
  const [parseError,     setParseError]     = useState<string | null>(null)
  const [parsedItems,    setParsedItems]    = useState<z.infer<typeof jsonItemSchema>[] | null>(null)
  const [progressItems,  setProgressItems]  = useState<ProgressItem[]>([])
  const [isUploading,    setIsUploading]    = useState(false)

  // ── 쿼리 / 뮤테이션 ─────────────────────────────────────

  const { data: documents = [], isLoading } = useQuery({
    queryKey: ['embeddings'],
    queryFn: listEmbeddings,
  })

  const createMutation = useMutation({
    mutationFn: createEmbedding,
    onSuccess: (data) => {
      toast.success(`"${data.title}" 임베딩이 생성되었습니다.`)
      form.reset()
      queryClient.invalidateQueries({ queryKey: ['embeddings'] })
    },
    onError: (err) => {
      logger.error('임베딩 생성 실패', err)
      toast.error('임베딩 생성에 실패했습니다.')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteEmbedding,
    onSuccess: () => {
      toast.success('문서가 삭제되었습니다.')
      queryClient.invalidateQueries({ queryKey: ['embeddings'] })
    },
    onError: (err) => {
      logger.error('문서 삭제 실패', err)
      toast.error('삭제에 실패했습니다.')
    },
    onSettled: () => setDeletingId(null),
  })

  // ── 핸들러 ──────────────────────────────────────────────

  const onSingleSubmit = (values: SingleValues) => createMutation.mutate(values)

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setFileName(file.name)
    setParsedItems(null)
    setParseError(null)
    setProgressItems([])

    const reader = new FileReader()
    reader.onload = (ev) => {
      try {
        const raw    = JSON.parse(ev.target?.result as string)
        const parsed = jsonFileSchema.parse(raw)
        setParsedItems(parsed)
      } catch (err) {
        if (err instanceof z.ZodError) {
          setParseError(`JSON 형식 오류: ${err.issues[0]?.message ?? '알 수 없는 오류'}`)
        } else {
          setParseError('JSON 파싱 실패. 올바른 JSON 파일인지 확인하세요.')
        }
      }
    }
    reader.readAsText(file)
    e.target.value = ''
  }

  const startUpload = async () => {
    if (!parsedItems || parsedItems.length === 0) return

    // 진행 목록 초기화 (모두 pending)
    const initial: ProgressItem[] = parsedItems.map(item => ({ ...item, status: 'pending' }))
    setProgressItems(initial)
    cancelledRef.current = false
    setIsUploading(true)

    let successCount = 0
    let errorCount   = 0

    for (let i = 0; i < initial.length; i++) {
      // 취소 확인
      if (cancelledRef.current) {
        setProgressItems(prev =>
          prev.map((p, idx) => idx >= i ? { ...p, status: 'cancelled' } : p)
        )
        break
      }

      // 처리 중 표시
      setProgressItems(prev =>
        prev.map((p, idx) => idx === i ? { ...p, status: 'processing' } : p)
      )

      try {
        const result = await createEmbedding({ title: initial[i].title, content: initial[i].desc })
        setProgressItems(prev =>
          prev.map((p, idx) =>
            idx === i ? { ...p, status: 'success', documentId: result.id } : p
          )
        )
        successCount++
      } catch (err) {
        const message = err instanceof Error ? err.message : '알 수 없는 오류'
        logger.error('다건 업로드 개별 실패', { id: initial[i].id, message })
        setProgressItems(prev =>
          prev.map((p, idx) => idx === i ? { ...p, status: 'error', error: message } : p)
        )
        errorCount++
      }
    }

    setIsUploading(false)
    queryClient.invalidateQueries({ queryKey: ['embeddings'] })

    if (cancelledRef.current) {
      toast.warning(`업로드가 취소되었습니다. (완료 ${successCount}건)`)
    } else if (errorCount === 0) {
      toast.success(`${successCount}건 모두 업로드 완료되었습니다.`)
    } else {
      toast.warning(`${successCount}건 성공, ${errorCount}건 실패했습니다.`)
    }
  }

  const cancelUpload = () => { cancelledRef.current = true }

  const resetBulk = () => {
    setParsedItems(null)
    setProgressItems([])
    setParseError(null)
    setFileName(null)
    cancelledRef.current = false
  }

  // ── 진행 통계 (파생값) ──────────────────────────────────

  const doneCount    = progressItems.filter(p => p.status === 'success' || p.status === 'error').length
  const successCount = progressItems.filter(p => p.status === 'success').length
  const errorCount   = progressItems.filter(p => p.status === 'error').length
  const totalCount   = progressItems.length
  const progressPct  = totalCount > 0 ? Math.round((doneCount / totalCount) * 100) : 0

  const isStarted  = progressItems.length > 0
  const isFinished = isStarted && !isUploading

  // ── 렌더 ────────────────────────────────────────────────

  return (
    <>
      <Header>
        <h1 className='text-lg font-semibold'>임베딩 관리</h1>
      </Header>
      <Main>
        <div className='space-y-6'>

          {/* 임베딩 생성 */}
          <Card>
            <CardHeader>
              <CardTitle className='text-base'>임베딩 생성</CardTitle>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue='single'>
                <TabsList className='mb-4'>
                  <TabsTrigger value='single'>단건 입력</TabsTrigger>
                  <TabsTrigger value='bulk'>JSON 파일 업로드</TabsTrigger>
                </TabsList>

                {/* ── 단건 입력 ── */}
                <TabsContent value='single'>
                  <Form {...form}>
                    <form onSubmit={form.handleSubmit(onSingleSubmit)} className='space-y-4'>
                      <FormField
                        control={form.control}
                        name='title'
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>제목</FormLabel>
                            <FormControl>
                              <Input placeholder='문서 제목을 입력하세요' {...field} />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      <FormField
                        control={form.control}
                        name='content'
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>내용</FormLabel>
                            <FormControl>
                              <Textarea
                                placeholder='임베딩할 텍스트 내용을 입력하세요'
                                className='min-h-[120px] resize-none'
                                {...field}
                              />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      <Button type='submit' disabled={createMutation.isPending}>
                        {createMutation.isPending
                          ? <><Loader2 className='mr-2 h-4 w-4 animate-spin' />임베딩 생성 중...</>
                          : <><Plus    className='mr-2 h-4 w-4' />임베딩 생성</>}
                      </Button>
                    </form>
                  </Form>
                </TabsContent>

                {/* ── JSON 파일 업로드 ── */}
                <TabsContent value='bulk'>
                  <div className='space-y-4'>

                    {/* 포맷 안내 */}
                    <div className='rounded-md bg-muted px-4 py-3 text-xs text-muted-foreground'>
                      <p className='mb-1 font-medium'>JSON 파일 형식</p>
                      <pre className='font-mono'>{`[\n  { "id": 1, "title": "제목", "desc": "내용" },\n  { "id": 2, "title": "제목2", "desc": "내용2" }\n]`}</pre>
                    </div>

                    {/* 파일 선택 */}
                    <div className='flex items-center gap-3'>
                      <input
                        ref={fileInputRef}
                        type='file'
                        accept='.json,application/json'
                        className='hidden'
                        onChange={onFileChange}
                        disabled={isUploading}
                      />
                      <Button
                        variant='outline'
                        onClick={() => fileInputRef.current?.click()}
                        disabled={isUploading}
                      >
                        <FileJson className='mr-2 h-4 w-4' />
                        JSON 파일 선택
                      </Button>
                      {fileName && (
                        <span className='text-sm text-muted-foreground'>{fileName}</span>
                      )}
                    </div>

                    {/* 파싱 오류 */}
                    {parseError && (
                      <p className='text-sm text-destructive'>{parseError}</p>
                    )}

                    {/* 미리보기 — 파일 파싱 완료, 아직 업로드 시작 전 */}
                    {parsedItems && !isStarted && (
                      <div className='space-y-3'>
                        <p className='text-sm text-muted-foreground'>
                          파싱 완료 —{' '}
                          <span className='font-medium text-foreground'>{parsedItems.length}건</span>{' '}
                          확인됨
                        </p>
                        <div className='max-h-48 overflow-y-auto rounded-md border'>
                          <Table>
                            <TableHeader>
                              <TableRow>
                                <TableHead className='w-20'>ID</TableHead>
                                <TableHead className='w-48'>제목</TableHead>
                                <TableHead>내용(desc)</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {parsedItems.map(item => (
                                <TableRow key={String(item.id)}>
                                  <TableCell className='text-muted-foreground'>{item.id}</TableCell>
                                  <TableCell className='font-medium'>{item.title}</TableCell>
                                  <TableCell className='max-w-xs truncate text-sm text-muted-foreground'>
                                    {item.desc.length > 80 ? `${item.desc.slice(0, 80)}...` : item.desc}
                                  </TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </div>
                        <div className='flex gap-2'>
                          <Button onClick={startUpload}>
                            <Upload className='mr-2 h-4 w-4' />
                            업로드 시작 ({parsedItems.length}건)
                          </Button>
                          <Button variant='ghost' onClick={resetBulk}>초기화</Button>
                        </div>
                      </div>
                    )}

                    {/* 진행 목록 — 업로드 시작 후 */}
                    {isStarted && (
                      <div className='space-y-3'>

                        {/* 진행률 바 */}
                        <div className='space-y-1'>
                          <div className='flex items-center justify-between text-sm'>
                            <span className='text-muted-foreground'>
                              {isUploading ? '처리 중...' : '완료'}
                            </span>
                            <span className='font-medium'>
                              {doneCount} / {totalCount}건
                              {successCount > 0 && (
                                <span className='ml-2 text-green-600'>✓{successCount}</span>
                              )}
                              {errorCount > 0 && (
                                <span className='ml-1 text-destructive'>✗{errorCount}</span>
                              )}
                            </span>
                          </div>
                          <div className='h-2 w-full overflow-hidden rounded-full bg-muted'>
                            <div
                              className='h-full bg-primary transition-all duration-300'
                              style={{ width: `${progressPct}%` }}
                            />
                          </div>
                        </div>

                        {/* 건별 상태 목록 */}
                        <div className='max-h-72 overflow-y-auto rounded-md border'>
                          <Table>
                            <TableHeader>
                              <TableRow>
                                <TableHead className='w-10'></TableHead>
                                <TableHead className='w-20'>ID</TableHead>
                                <TableHead>제목</TableHead>
                                <TableHead className='w-24'>DB ID</TableHead>
                                <TableHead>오류</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {progressItems.map((item, idx) => (
                                <TableRow key={String(item.id) + idx} className={rowBg(item.status)}>
                                  <TableCell>
                                    <StatusIcon status={item.status} />
                                  </TableCell>
                                  <TableCell className='text-muted-foreground'>{item.id}</TableCell>
                                  <TableCell className='font-medium'>{item.title}</TableCell>
                                  <TableCell className='text-muted-foreground'>
                                    {item.documentId ?? '-'}
                                  </TableCell>
                                  <TableCell className='max-w-xs truncate text-xs text-destructive'>
                                    {item.error ?? ''}
                                  </TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </div>

                        {/* 액션 버튼 */}
                        <div className='flex gap-2'>
                          {isUploading ? (
                            <Button variant='destructive' size='sm' onClick={cancelUpload}>
                              취소
                            </Button>
                          ) : (
                            <>
                              {isFinished && (
                                <div className='flex items-center gap-2'>
                                  <Badge variant='secondary'>전체 {totalCount}건</Badge>
                                  {successCount > 0 && (
                                    <Badge className='bg-green-500 text-white hover:bg-green-600'>
                                      성공 {successCount}건
                                    </Badge>
                                  )}
                                  {errorCount > 0 && (
                                    <Badge variant='destructive'>실패 {errorCount}건</Badge>
                                  )}
                                </div>
                              )}
                              <Button variant='outline' size='sm' onClick={resetBulk}>
                                다시 업로드
                              </Button>
                            </>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>

          {/* 저장된 문서 목록 */}
          <Card>
            <CardHeader>
              <CardTitle className='text-base'>
                저장된 문서
                <Badge variant='secondary' className='ml-2'>{documents.length}건</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className='flex items-center justify-center py-12'>
                  <Loader2 className='h-6 w-6 animate-spin text-muted-foreground' />
                </div>
              ) : documents.length === 0 ? (
                <div className='py-12 text-center text-sm text-muted-foreground'>
                  저장된 문서가 없습니다. 위에서 임베딩을 생성해보세요.
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className='w-16'>ID</TableHead>
                      <TableHead className='w-48'>제목</TableHead>
                      <TableHead>내용</TableHead>
                      <TableHead className='w-40'>모델</TableHead>
                      <TableHead className='w-44'>생성일시</TableHead>
                      <TableHead className='w-16'></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {documents.map(doc => (
                      <TableRow key={doc.id}>
                        <TableCell className='text-muted-foreground'>{doc.id}</TableCell>
                        <TableCell className='font-medium'>{doc.title}</TableCell>
                        <TableCell className='max-w-xs truncate text-sm text-muted-foreground'>
                          {doc.content.length > 100 ? `${doc.content.slice(0, 100)}...` : doc.content}
                        </TableCell>
                        <TableCell>
                          <Badge variant='outline' className='text-xs'>{doc.model}</Badge>
                        </TableCell>
                        <TableCell className='text-sm text-muted-foreground'>
                          {new Date(doc.createdAt).toLocaleString('ko-KR')}
                        </TableCell>
                        <TableCell>
                          <AlertDialog>
                            <AlertDialogTrigger asChild>
                              <Button
                                variant='ghost'
                                size='icon'
                                className='h-8 w-8 text-muted-foreground hover:text-destructive'
                                onClick={() => setDeletingId(doc.id)}
                              >
                                <Trash2 className='h-4 w-4' />
                              </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                              <AlertDialogHeader>
                                <AlertDialogTitle>문서 삭제</AlertDialogTitle>
                                <AlertDialogDescription>
                                  &quot;{doc.title}&quot; 문서를 삭제합니다. 이 작업은 되돌릴 수 없습니다.
                                </AlertDialogDescription>
                              </AlertDialogHeader>
                              <AlertDialogFooter>
                                <AlertDialogCancel onClick={() => setDeletingId(null)}>취소</AlertDialogCancel>
                                <AlertDialogAction
                                  onClick={() => deleteMutation.mutate(doc.id)}
                                  disabled={deleteMutation.isPending && deletingId === doc.id}
                                  className='bg-destructive text-destructive-foreground hover:bg-destructive/90'
                                >
                                  {deleteMutation.isPending && deletingId === doc.id ? '삭제 중...' : '삭제'}
                                </AlertDialogAction>
                              </AlertDialogFooter>
                            </AlertDialogContent>
                          </AlertDialog>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </div>
      </Main>
    </>
  )
}
