'use client'

import { useEffect, useState } from 'react'
import { Wand2 } from 'lucide-react'
import { type AiOverviewDocumentSummary } from '@/api/ai-overview'
import { getChatModels, type ChatModel } from '@/api/llm-resources'
import { logger } from '@/lib/logger'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'

export const DEFAULT_KEYWORD_PROMPT =
  '문서에서 검색에 사용될 핵심 키워드와 동의어를 추출하세요.\n\n추출 기준:\n- 핵심 명사, 업무 용어, 고유 명사 중심\n- 동의어는 같은 개념의 다른 표현(약어, 한자어, 영문 혼용 등)'

const FORMAT_PREVIEW =
  '반드시 다음 JSON 형식만 반환하세요 (설명 없이):\n{\n  "keywords": ["키워드1", "키워드2"],\n  "synonyms": {\n    "키워드1": ["동의어A", "동의어B"],\n    "키워드2": ["동의어C"]\n  }\n}'

interface Props {
  open: boolean
  doc: AiOverviewDocumentSummary | null
  onOpenChange: (open: boolean) => void
  onGenerate: (doc: AiOverviewDocumentSummary, systemPrompt: string, model?: string) => void
  isGenerating: boolean
}

export function KeywordPromptDialog({ open, doc, onOpenChange, onGenerate, isGenerating }: Props) {
  const [prompt, setPrompt] = useState(DEFAULT_KEYWORD_PROMPT)
  const [selectedModel, setSelectedModel] = useState<string>('')
  const [chatModels, setChatModels] = useState<ChatModel[]>([])

  useEffect(() => {
    getChatModels().then(setChatModels).catch((e) => logger.error('Failed to load chat models', e))
  }, [])

  const handleOpenChange = (v: boolean) => {
    if (!v) {
      setPrompt(DEFAULT_KEYWORD_PROMPT)
      setSelectedModel('')
    }
    onOpenChange(v)
  }

  const handleGenerate = () => {
    if (!doc) return
    const model = selectedModel || undefined
    onGenerate(doc, prompt, model)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className='max-w-lg'>
        <DialogHeader>
          <DialogTitle>키워드 생성</DialogTitle>
          <DialogDescription className='line-clamp-1'>{doc?.title}</DialogDescription>
        </DialogHeader>

        <div className='flex flex-col gap-3'>
          <div className='flex flex-col gap-1.5'>
            <Label>LLM 모델</Label>
            <Select value={selectedModel} onValueChange={setSelectedModel}>
              <SelectTrigger>
                <SelectValue placeholder='기본 모델 사용' />
              </SelectTrigger>
              <SelectContent>
                {chatModels.length === 0 ? (
                  <SelectItem value='__none__' disabled>
                    등록된 모델 없음
                  </SelectItem>
                ) : (
                  chatModels.map((m) => (
                    <SelectItem key={m.id} value={m.modelName ?? m.name}>
                      {m.modelName ?? m.name}
                    </SelectItem>
                  ))
                )}
              </SelectContent>
            </Select>
          </div>

          <div className='flex flex-col gap-1.5'>
            <Label>시스템 프롬프트</Label>
            <Textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows={6}
              placeholder='키워드 추출 지침을 입력하세요'
              className='resize-none text-sm'
            />
          </div>

          <div className='flex flex-col gap-1.5'>
            <Label className='text-muted-foreground text-xs'>자동 추가되는 포맷 지침 (변경 불가)</Label>
            <pre className='rounded-md border bg-muted/50 px-3 py-2 text-xs text-muted-foreground whitespace-pre-wrap'>
              {FORMAT_PREVIEW}
            </pre>
          </div>
        </div>

        <DialogFooter>
          <Button variant='outline' onClick={() => handleOpenChange(false)} disabled={isGenerating}>
            취소
          </Button>
          <Button onClick={handleGenerate} disabled={!prompt.trim() || isGenerating}>
            <Wand2 className={`mr-2 h-4 w-4 ${isGenerating ? 'animate-spin' : ''}`} />
            {isGenerating ? '생성 중...' : '키워드 생성'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
