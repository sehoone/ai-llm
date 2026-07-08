'use client'

import { ExternalLink } from 'lucide-react'
import { type AiOverviewDocumentDetail } from '@/api/ai-overview'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Separator } from '@/components/ui/separator'

const STATUS_BADGE: Record<string, { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }> = {
  pending:    { label: '대기',    variant: 'secondary' },
  processing: { label: '처리중', variant: 'outline' },
  ready:      { label: '완료',   variant: 'default' },
  error:      { label: '오류',   variant: 'destructive' },
}

interface Props {
  open: boolean
  doc: AiOverviewDocumentDetail | null
  loading: boolean
  onOpenChange: (open: boolean) => void
}

export function DocumentDetailDialog({ open, doc, loading, onOpenChange }: Props) {
  const badge = doc ? (STATUS_BADGE[doc.status] ?? STATUS_BADGE.pending) : null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className='max-w-2xl max-h-[80vh] flex flex-col'>
        <DialogHeader>
          <DialogTitle className='pr-6 line-clamp-2'>
            {loading ? '불러오는 중...' : (doc?.title ?? '')}
          </DialogTitle>
          {doc && (
            <div className='flex flex-wrap items-center gap-2 pt-1'>
              <Badge variant={badge!.variant}>{badge!.label}</Badge>
              <span className='text-xs text-muted-foreground'>
                키워드 {doc.keyword_count}개
              </span>
              <span className='text-xs text-muted-foreground'>
                {new Date(doc.created_at).toLocaleDateString('ko-KR')}
              </span>
              {doc.source_url && (
                <a
                  href={doc.source_url}
                  target='_blank'
                  rel='noopener noreferrer'
                  className='inline-flex items-center gap-1 text-xs text-primary hover:underline'
                >
                  <ExternalLink className='h-3 w-3' />
                  원본 링크
                </a>
              )}
            </div>
          )}
        </DialogHeader>

        {loading && (
          <div className='flex-1 flex items-center justify-center py-10 text-sm text-muted-foreground'>
            불러오는 중...
          </div>
        )}

        {!loading && doc && (
          <div className='flex-1 overflow-y-auto flex flex-col gap-4 min-h-0'>
            {/* 본문 */}
            <div className='flex flex-col gap-1.5'>
              <p className='text-xs font-medium text-muted-foreground uppercase tracking-wide'>본문</p>
              <pre className='whitespace-pre-wrap text-sm leading-relaxed rounded-md border bg-muted/30 p-4 overflow-x-auto'>
                {doc.content}
              </pre>
            </div>

            {/* 키워드 */}
            {doc.keywords.length > 0 && (
              <>
                <Separator />
                <div className='flex flex-col gap-2'>
                  <p className='text-xs font-medium text-muted-foreground uppercase tracking-wide'>
                    키워드 ({doc.keywords.length}개)
                  </p>
                  <div className='flex flex-wrap gap-1.5'>
                    {doc.keywords.map((kw) => (
                      <Badge
                        key={kw.id}
                        variant={kw.keyword_type === 'keyword' ? 'default' : 'secondary'}
                        className='text-xs'
                      >
                        {kw.keyword}
                      </Badge>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
