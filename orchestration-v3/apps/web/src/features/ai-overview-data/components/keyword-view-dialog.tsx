'use client'

import { useState } from 'react'
import { toast } from 'sonner'
import { Trash2, Tag } from 'lucide-react'
import { aiOverviewApi, type AiOverviewKeyword } from '@/api/ai-overview'
import { logger } from '@/lib/logger'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Separator } from '@/components/ui/separator'

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  docId: number
  docTitle: string
  keywords: AiOverviewKeyword[]
  onKeywordsChange: (keywords: AiOverviewKeyword[]) => void
}

export function KeywordViewDialog({
  open,
  onOpenChange,
  docId,
  docTitle,
  keywords,
  onKeywordsChange,
}: Props) {
  const [deletingId, setDeletingId] = useState<number | null>(null)

  const keywordItems = keywords.filter((k) => k.keyword_type === 'keyword')
  const synonymItems = keywords.filter((k) => k.keyword_type === 'synonym')

  const handleDelete = async (keyword: AiOverviewKeyword) => {
    setDeletingId(keyword.id)
    try {
      await aiOverviewApi.deleteKeyword(docId, keyword.id)
      onKeywordsChange(keywords.filter((k) => k.id !== keyword.id))
      toast.success(`'${keyword.keyword}' 삭제됨`)
    } catch (error) {
      logger.error(error)
      toast.error('키워드 삭제에 실패했습니다')
    } finally {
      setDeletingId(null)
    }
  }

  const KeywordRow = ({ kw }: { kw: AiOverviewKeyword }) => (
    <div className='flex items-center justify-between gap-2 py-1'>
      <div className='flex items-center gap-2'>
        <Badge
          variant={kw.keyword_type === 'keyword' ? 'default' : 'secondary'}
          className='text-xs px-1.5 py-0'
        >
          {kw.keyword_type === 'keyword' ? '키워드' : '동의어'}
        </Badge>
        <span className='text-sm'>{kw.keyword}</span>
      </div>
      <Button
        variant='ghost'
        size='icon'
        className='h-6 w-6 text-muted-foreground hover:text-destructive'
        disabled={deletingId === kw.id}
        onClick={() => handleDelete(kw)}
      >
        <Trash2 className='h-3 w-3' />
      </Button>
    </div>
  )

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className='max-w-lg max-h-[70vh] overflow-y-auto'>
        <DialogHeader>
          <DialogTitle className='flex items-center gap-2'>
            <Tag className='h-4 w-4' />
            키워드 관리
          </DialogTitle>
          <DialogDescription className='truncate'>{docTitle}</DialogDescription>
        </DialogHeader>

        {keywords.length === 0 ? (
          <p className='text-sm text-muted-foreground py-4 text-center'>
            키워드가 없습니다. 키워드 생성을 실행하세요.
          </p>
        ) : (
          <div className='flex flex-col gap-3'>
            {keywordItems.length > 0 && (
              <div>
                <p className='text-xs font-semibold text-muted-foreground mb-1'>
                  핵심 키워드 ({keywordItems.length})
                </p>
                <div className='divide-y divide-border/50'>
                  {keywordItems.map((kw) => <KeywordRow key={kw.id} kw={kw} />)}
                </div>
              </div>
            )}
            {keywordItems.length > 0 && synonymItems.length > 0 && <Separator />}
            {synonymItems.length > 0 && (
              <div>
                <p className='text-xs font-semibold text-muted-foreground mb-1'>
                  동의어 ({synonymItems.length})
                </p>
                <div className='divide-y divide-border/50'>
                  {synonymItems.map((kw) => <KeywordRow key={kw.id} kw={kw} />)}
                </div>
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
