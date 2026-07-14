'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation } from '@tanstack/react-query'
import { toast } from 'sonner'
import { SearchIcon, Loader2 } from 'lucide-react'
import { searchEmbeddings, type SearchResult } from '@/api/embeddings'
import { logger } from '@/lib/logger'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Header } from '@/components/layout/header'
import { Main } from '@/components/layout/main'

const formSchema = z.object({
  query: z.string().min(1, '검색어를 입력하세요'),
  topK: z.number().min(1).max(20),
  threshold: z.number().min(0).max(1),
})

type FormValues = z.infer<typeof formSchema>

function ScoreBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100)
  if (pct >= 90) {
    return <Badge className='bg-green-500 text-white hover:bg-green-600'>{pct}%</Badge>
  }
  if (pct >= 70) {
    return <Badge className='bg-yellow-500 text-white hover:bg-yellow-600'>{pct}%</Badge>
  }
  return <Badge variant='secondary'>{pct}%</Badge>
}

function ScoreBar({ score }: { score: number }) {
  const pct = Math.round(score * 100)
  const colorClass =
    pct >= 90 ? 'bg-green-500' : pct >= 70 ? 'bg-yellow-500' : 'bg-gray-400'

  return (
    <div className='flex items-center gap-2'>
      <div className='h-2 w-32 overflow-hidden rounded-full bg-muted'>
        <div className={`h-full ${colorClass} transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <ScoreBadge score={score} />
    </div>
  )
}

export function SearchFeature() {
  const [results, setResults] = useState<SearchResult[] | null>(null)
  const [selected, setSelected] = useState<SearchResult | null>(null)

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: { query: '', topK: 5, threshold: 0.7 },
  })

  const searchMutation = useMutation({
    mutationFn: searchEmbeddings,
    onSuccess: (data) => {
      setResults(data)
      if (data.length === 0) {
        toast.info('검색 결과가 없습니다.')
      }
    },
    onError: (err) => {
      logger.error('벡터 검색 실패', err)
      toast.error('검색에 실패했습니다.')
    },
  })

  const onSubmit = (values: FormValues) => {
    searchMutation.mutate(values)
  }

  const handleQueryKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      form.handleSubmit(onSubmit)()
    }
  }

  return (
    <>
      <Header>
        <h1 className='text-lg font-semibold'>벡터 검색</h1>
      </Header>
      <Main>
        <div className='space-y-6'>
          {/* 검색 폼 */}
          <Card>
            <CardHeader>
              <CardTitle className='text-base'>코사인 유사도 검색</CardTitle>
            </CardHeader>
            <CardContent>
              <Form {...form}>
                <form
                  onSubmit={form.handleSubmit(onSubmit)}
                  className='flex flex-col gap-4 sm:flex-row sm:items-end'
                >
                  <FormField
                    control={form.control}
                    name='query'
                    render={({ field }) => (
                      <FormItem className='flex-1'>
                        <FormLabel>검색어</FormLabel>
                        <FormControl>
                          <Textarea
                            placeholder='검색할 내용을 입력하세요 (Enter: 검색, Shift+Enter: 줄바꿈)'
                            className='min-h-[80px] resize-none'
                            onKeyDown={handleQueryKeyDown}
                            {...field}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name='topK'
                    render={({ field }) => (
                      <FormItem className='w-28'>
                        <FormLabel>결과 수</FormLabel>
                        <Select
                          value={String(field.value)}
                          onValueChange={(v) => field.onChange(Number(v))}
                        >
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value='3'>3개</SelectItem>
                            <SelectItem value='5'>5개</SelectItem>
                            <SelectItem value='10'>10개</SelectItem>
                            <SelectItem value='20'>20개</SelectItem>
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name='threshold'
                    render={({ field }) => (
                      <FormItem className='w-32'>
                        <FormLabel>유사도 임계값</FormLabel>
                        <Select
                          value={String(field.value)}
                          onValueChange={(v) => field.onChange(Number(v))}
                        >
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value='0.5'>0.5 (낮음)</SelectItem>
                            <SelectItem value='0.6'>0.6</SelectItem>
                            <SelectItem value='0.7'>0.7 (기본)</SelectItem>
                            <SelectItem value='0.8'>0.8</SelectItem>
                            <SelectItem value='0.9'>0.9 (높음)</SelectItem>
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <Button type='submit' disabled={searchMutation.isPending} className='sm:mb-0'>
                    {searchMutation.isPending ? (
                      <>
                        <Loader2 className='mr-2 h-4 w-4 animate-spin' />
                        검색 중...
                      </>
                    ) : (
                      <>
                        <SearchIcon className='mr-2 h-4 w-4' />
                        검색
                      </>
                    )}
                  </Button>
                </form>
              </Form>
            </CardContent>
          </Card>

          {/* 검색 결과 */}
          {results === null ? (
            <div className='py-16 text-center text-sm text-muted-foreground'>
              검색어를 입력하고 검색 버튼을 눌러주세요.
              <br />
              저장된 문서 중 의미적으로 유사한 결과를 검색합니다.
            </div>
          ) : results.length === 0 ? (
            <div className='py-16 text-center text-sm text-muted-foreground'>
              유사한 문서를 찾을 수 없습니다.
            </div>
          ) : (
            <div className='space-y-3'>
              <p className='text-sm text-muted-foreground'>
                유사 문서 {results.length}건 (유사도 높은 순 · 임계값 {form.getValues('threshold')})
              </p>
              {results.map((result, idx) => (
                <Card
                  key={result.id}
                  className='cursor-pointer transition-shadow hover:shadow-md'
                  onClick={() => setSelected(result)}
                >
                  <CardContent className='pt-4'>
                    <div className='flex items-start justify-between gap-4'>
                      <div className='flex-1 space-y-2'>
                        <div className='flex items-center gap-2'>
                          <span className='text-xs font-medium text-muted-foreground'>
                            #{idx + 1}
                          </span>
                          <h3 className='font-semibold'>{result.title}</h3>
                        </div>
                        <p className='line-clamp-2 text-sm leading-relaxed text-muted-foreground'>
                          {result.content}
                        </p>
                        <p className='text-xs text-muted-foreground'>
                          {new Date(result.createdAt).toLocaleString('ko-KR')}
                        </p>
                      </div>
                      <div className='flex flex-col items-end gap-1'>
                        <span className='text-xs text-muted-foreground'>유사도</span>
                        <ScoreBar score={result.score} />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}

              {/* 상세 팝업 */}
              <Dialog open={!!selected} onOpenChange={(open) => !open && setSelected(null)}>
                <DialogContent className='max-w-xl'>
                  <DialogHeader>
                    <DialogTitle>{selected?.title}</DialogTitle>
                    <DialogDescription asChild>
                      <div className='flex items-center gap-2 pt-1'>
                        {selected && <ScoreBadge score={selected.score} />}
                        <span className='text-xs text-muted-foreground'>
                          {selected ? `유사도 ${Math.round(selected.score * 100)}%` : ''}
                        </span>
                      </div>
                    </DialogDescription>
                  </DialogHeader>
                  <Separator />
                  <div className='space-y-3'>
                    <p className='text-sm leading-relaxed whitespace-pre-wrap'>{selected?.content}</p>
                  </div>
                  <Separator />
                  <div className='flex justify-between text-xs text-muted-foreground'>
                    <span>ID: {selected?.id}</span>
                    <span>
                      {selected ? new Date(selected.createdAt).toLocaleString('ko-KR') : ''}
                    </span>
                  </div>
                </DialogContent>
              </Dialog>
            </div>
          )}
        </div>
      </Main>
    </>
  )
}
