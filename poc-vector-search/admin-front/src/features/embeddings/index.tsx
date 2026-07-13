'use client'

import { useRef, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Trash2, Plus, Loader2, Upload, FileJson, CheckCircle2, XCircle } from 'lucide-react'
import {
  createEmbedding,
  deleteEmbedding,
  listEmbeddings,
  bulkUploadEmbeddings,
  type BulkEmbeddingItem,
  type BulkEmbeddingResponse,
} from '@/api/embeddings'
import { logger } from '@/lib/logger'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Header } from '@/components/layout/header'
import { Main } from '@/components/layout/main'

// ── 단건 입력 폼 ────────────────────────────────────────────

const formSchema = z.object({
  title: z.string().min(1, '제목을 입력하세요').max(500),
  content: z.string().min(1, '내용을 입력하세요'),
})
type FormValues = z.infer<typeof formSchema>

// ── JSON 파일 스키마 ────────────────────────────────────────

const jsonItemSchema = z.object({
  id: z.union([z.string(), z.number()]),
  title: z.string().min(1),
  desc: z.string().min(1),
})
const jsonFileSchema = z.array(jsonItemSchema).min(1, '항목이 1건 이상이어야 합니다.')

// ── 메인 컴포넌트 ───────────────────────────────────────────

export function EmbeddingsFeature() {
  const queryClient = useQueryClient()
  const [deletingId, setDeletingId] = useState<number | null>(null)

  // 단건 폼
  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: { title: '', content: '' },
  })

  // JSON 업로드 상태
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [parsedItems, setParsedItems] = useState<BulkEmbeddingItem[] | null>(null)
  const [parseError, setParseError] = useState<string | null>(null)
  const [fileName, setFileName] = useState<string | null>(null)
  const [bulkResult, setBulkResult] = useState<BulkEmbeddingResponse | null>(null)

  // ── 쿼리 / 뮤테이션 ──────────────────────────────────────

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

  const bulkMutation = useMutation({
    mutationFn: bulkUploadEmbeddings,
    onSuccess: (data) => {
      setBulkResult(data)
      queryClient.invalidateQueries({ queryKey: ['embeddings'] })
      if (data.failedCount === 0) {
        toast.success(`${data.successCount}건 모두 업로드 완료되었습니다.`)
      } else {
        toast.warning(`${data.successCount}건 성공, ${data.failedCount}건 실패했습니다.`)
      }
    },
    onError: (err) => {
      logger.error('일괄 업로드 실패', err)
      toast.error('업로드 중 오류가 발생했습니다.')
    },
  })

  // ── 핸들러 ───────────────────────────────────────────────

  const onSingleSubmit = (values: FormValues) => {
    createMutation.mutate(values)
  }

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setFileName(file.name)
    setParsedItems(null)
    setParseError(null)
    setBulkResult(null)

    const reader = new FileReader()
    reader.onload = (ev) => {
      try {
        const raw = JSON.parse(ev.target?.result as string)
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

    // 같은 파일 재선택 허용
    e.target.value = ''
  }

  const onBulkUpload = () => {
    if (!parsedItems) return
    setBulkResult(null)
    bulkMutation.mutate(parsedItems)
  }

  const resetFileUpload = () => {
    setParsedItems(null)
    setParseError(null)
    setFileName(null)
    setBulkResult(null)
  }

  // ── 렌더 ─────────────────────────────────────────────────

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

                {/* 단건 입력 */}
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
                        {createMutation.isPending ? (
                          <>
                            <Loader2 className='mr-2 h-4 w-4 animate-spin' />
                            임베딩 생성 중...
                          </>
                        ) : (
                          <>
                            <Plus className='mr-2 h-4 w-4' />
                            임베딩 생성
                          </>
                        )}
                      </Button>
                    </form>
                  </Form>
                </TabsContent>

                {/* JSON 파일 업로드 */}
                <TabsContent value='bulk'>
                  <div className='space-y-4'>
                    {/* 포맷 안내 */}
                    <div className='rounded-md bg-muted px-4 py-3 text-xs text-muted-foreground'>
                      <p className='mb-1 font-medium'>JSON 파일 형식</p>
                      <pre className='font-mono'>{`[
  { "id": 1, "title": "제목", "desc": "내용" },
  { "id": 2, "title": "제목2", "desc": "내용2" }
]`}</pre>
                    </div>

                    {/* 파일 선택 */}
                    <div className='flex items-center gap-3'>
                      <input
                        ref={fileInputRef}
                        type='file'
                        accept='.json,application/json'
                        className='hidden'
                        onChange={onFileChange}
                      />
                      <Button
                        variant='outline'
                        onClick={() => fileInputRef.current?.click()}
                        disabled={bulkMutation.isPending}
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

                    {/* 파일 미리보기 */}
                    {parsedItems && parsedItems.length > 0 && !bulkResult && (
                      <div className='space-y-3'>
                        <p className='text-sm text-muted-foreground'>
                          파싱 완료 —{' '}
                          <span className='font-medium text-foreground'>{parsedItems.length}건</span>{' '}
                          확인됨
                        </p>
                        <div className='max-h-56 overflow-y-auto rounded-md border'>
                          <Table>
                            <TableHeader>
                              <TableRow>
                                <TableHead className='w-20'>ID</TableHead>
                                <TableHead className='w-48'>제목</TableHead>
                                <TableHead>내용(desc)</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {parsedItems.map((item) => (
                                <TableRow key={String(item.id)}>
                                  <TableCell className='text-muted-foreground'>
                                    {item.id}
                                  </TableCell>
                                  <TableCell className='font-medium'>{item.title}</TableCell>
                                  <TableCell className='max-w-xs truncate text-sm text-muted-foreground'>
                                    {item.desc.length > 80
                                      ? `${item.desc.slice(0, 80)}...`
                                      : item.desc}
                                  </TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </div>
                        <div className='flex gap-2'>
                          <Button onClick={onBulkUpload} disabled={bulkMutation.isPending}>
                            {bulkMutation.isPending ? (
                              <>
                                <Loader2 className='mr-2 h-4 w-4 animate-spin' />
                                업로드 중... ({parsedItems.length}건)
                              </>
                            ) : (
                              <>
                                <Upload className='mr-2 h-4 w-4' />
                                일괄 업로드 ({parsedItems.length}건)
                              </>
                            )}
                          </Button>
                          <Button variant='ghost' onClick={resetFileUpload}>
                            초기화
                          </Button>
                        </div>
                      </div>
                    )}

                    {/* 업로드 결과 */}
                    {bulkResult && (
                      <div className='space-y-3'>
                        <div className='flex items-center gap-3'>
                          <Badge variant='secondary'>전체 {bulkResult.total}건</Badge>
                          <Badge className='bg-green-500 text-white hover:bg-green-600'>
                            성공 {bulkResult.successCount}건
                          </Badge>
                          {bulkResult.failedCount > 0 && (
                            <Badge variant='destructive'>실패 {bulkResult.failedCount}건</Badge>
                          )}
                        </div>
                        <div className='max-h-64 overflow-y-auto rounded-md border'>
                          <Table>
                            <TableHeader>
                              <TableRow>
                                <TableHead className='w-16'></TableHead>
                                <TableHead className='w-20'>ID</TableHead>
                                <TableHead>제목</TableHead>
                                <TableHead className='w-24'>DB ID</TableHead>
                                <TableHead>오류</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {bulkResult.results.map((r) => (
                                <TableRow key={String(r.id)}>
                                  <TableCell>
                                    {r.success ? (
                                      <CheckCircle2 className='h-4 w-4 text-green-500' />
                                    ) : (
                                      <XCircle className='h-4 w-4 text-destructive' />
                                    )}
                                  </TableCell>
                                  <TableCell className='text-muted-foreground'>{r.id}</TableCell>
                                  <TableCell className='font-medium'>{r.title}</TableCell>
                                  <TableCell className='text-muted-foreground'>
                                    {r.documentId ?? '-'}
                                  </TableCell>
                                  <TableCell className='text-sm text-destructive'>
                                    {r.error ?? ''}
                                  </TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </div>
                        <Button variant='outline' size='sm' onClick={resetFileUpload}>
                          다시 업로드
                        </Button>
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
                <Badge variant='secondary' className='ml-2'>
                  {documents.length}건
                </Badge>
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
                    {documents.map((doc) => (
                      <TableRow key={doc.id}>
                        <TableCell className='text-muted-foreground'>{doc.id}</TableCell>
                        <TableCell className='font-medium'>{doc.title}</TableCell>
                        <TableCell className='max-w-xs truncate text-sm text-muted-foreground'>
                          {doc.content.length > 100
                            ? `${doc.content.slice(0, 100)}...`
                            : doc.content}
                        </TableCell>
                        <TableCell>
                          <Badge variant='outline' className='text-xs'>
                            {doc.model}
                          </Badge>
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
                                  &quot;{doc.title}&quot; 문서를 삭제합니다. 이 작업은 되돌릴 수
                                  없습니다.
                                </AlertDialogDescription>
                              </AlertDialogHeader>
                              <AlertDialogFooter>
                                <AlertDialogCancel onClick={() => setDeletingId(null)}>
                                  취소
                                </AlertDialogCancel>
                                <AlertDialogAction
                                  onClick={() => deleteMutation.mutate(doc.id)}
                                  disabled={deleteMutation.isPending && deletingId === doc.id}
                                  className='bg-destructive text-destructive-foreground hover:bg-destructive/90'
                                >
                                  {deleteMutation.isPending && deletingId === doc.id
                                    ? '삭제 중...'
                                    : '삭제'}
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
