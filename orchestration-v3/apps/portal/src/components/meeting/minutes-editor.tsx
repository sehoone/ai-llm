'use client'

import { useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import type { ActionItem, DiscussionItem, MinutesContent } from '@/api/meetings'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'

const linesToArray = (s: string): string[] =>
  s.split('\n').map((l) => l.trim()).filter(Boolean)
const arrayToLines = (a?: string[]): string => (a ?? []).join('\n')

// portal은 shadcn Label을 복제하지 않는다(ADR-0020 린 구성) — plain <label>로 대체.
function FieldLabel({ children, htmlFor }: { children: React.ReactNode; htmlFor?: string }) {
  return (
    <label htmlFor={htmlFor} className='text-sm font-medium leading-none'>
      {children}
    </label>
  )
}

interface Props {
  content: MinutesContent
  saving: boolean
  onCancel: () => void
  onSave: (content: MinutesContent, summary: string) => void
}

export function MinutesEditor({ content, saving, onCancel, onSave }: Props) {
  const [title, setTitle] = useState(content.title ?? '')
  const [attendees, setAttendees] = useState((content.attendees ?? []).join(', '))
  const [agenda, setAgenda] = useState(arrayToLines(content.agenda))
  const [discussion, setDiscussion] = useState<DiscussionItem[]>(
    content.discussion ?? []
  )
  const [decisions, setDecisions] = useState(arrayToLines(content.decisions))
  const [actionItems, setActionItems] = useState<ActionItem[]>(content.action_items ?? [])
  const [summary, setSummary] = useState(content.summary ?? '')
  const [nextSteps, setNextSteps] = useState(arrayToLines(content.next_steps))

  const updateDiscussion = (i: number, patch: Partial<DiscussionItem>) =>
    setDiscussion((prev) => prev.map((d, idx) => (idx === i ? { ...d, ...patch } : d)))
  const updateAction = (i: number, patch: Partial<ActionItem>) =>
    setActionItems((prev) => prev.map((a, idx) => (idx === i ? { ...a, ...patch } : a)))

  const handleSave = () => {
    const next: MinutesContent = {
      title: title.trim(),
      attendees: attendees.split(',').map((a) => a.trim()).filter(Boolean),
      agenda: linesToArray(agenda),
      discussion: discussion
        .filter((d) => (d.topic ?? '').trim() || (d.points ?? []).length)
        .map((d) => ({
          topic: (d.topic ?? '').trim(),
          points: Array.isArray(d.points) ? d.points : linesToArray(String(d.points ?? '')),
          speakers: d.speakers ?? [],
        })),
      decisions: linesToArray(decisions),
      action_items: actionItems.filter((a) => (a.task ?? '').trim()),
      summary: summary.trim(),
      next_steps: linesToArray(nextSteps),
    }
    onSave(next, summary.trim())
  }

  return (
    <div className='flex h-[calc(100vh-16rem)] flex-col'>
      <div className='flex-1 overflow-y-auto'>
        <div className='space-y-4 p-4'>
          <div className='space-y-1.5'>
            <FieldLabel>제목</FieldLabel>
            <Input value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>

          <div className='space-y-1.5'>
            <FieldLabel>참석자 (쉼표로 구분)</FieldLabel>
            <Input value={attendees} onChange={(e) => setAttendees(e.target.value)} />
          </div>

          <div className='space-y-1.5'>
            <FieldLabel>안건 (줄바꿈으로 구분)</FieldLabel>
            <Textarea rows={3} value={agenda} onChange={(e) => setAgenda(e.target.value)} />
          </div>

          <div className='space-y-2'>
            <div className='flex items-center justify-between'>
              <FieldLabel>논의 내용</FieldLabel>
              <Button
                type='button'
                variant='ghost'
                size='sm'
                className='h-7'
                onClick={() => setDiscussion((prev) => [...prev, { topic: '', points: [] }])}
              >
                <Plus className='mr-1 h-3 w-3' /> 추가
              </Button>
            </div>
            {discussion.map((d, i) => (
              <div key={i} className='space-y-1.5 rounded-md border p-2'>
                <div className='flex items-center gap-2'>
                  <Input
                    placeholder='주제'
                    value={d.topic ?? ''}
                    onChange={(e) => updateDiscussion(i, { topic: e.target.value })}
                  />
                  <Button
                    type='button'
                    variant='ghost'
                    size='sm'
                    className='h-8 w-8 shrink-0 p-0'
                    onClick={() => setDiscussion((prev) => prev.filter((_, idx) => idx !== i))}
                  >
                    <Trash2 className='h-4 w-4' />
                  </Button>
                </div>
                <Textarea
                  rows={2}
                  placeholder='핵심 포인트 (줄바꿈으로 구분)'
                  value={arrayToLines(d.points)}
                  onChange={(e) => updateDiscussion(i, { points: linesToArray(e.target.value) })}
                />
              </div>
            ))}
          </div>

          <div className='space-y-1.5'>
            <FieldLabel>결정 사항 (줄바꿈으로 구분)</FieldLabel>
            <Textarea rows={3} value={decisions} onChange={(e) => setDecisions(e.target.value)} />
          </div>

          <div className='space-y-2'>
            <div className='flex items-center justify-between'>
              <FieldLabel>액션 아이템</FieldLabel>
              <Button
                type='button'
                variant='ghost'
                size='sm'
                className='h-7'
                onClick={() => setActionItems((prev) => [...prev, { task: '', owner: '', due: '' }])}
              >
                <Plus className='mr-1 h-3 w-3' /> 추가
              </Button>
            </div>
            {actionItems.map((a, i) => (
              <div key={i} className='flex items-center gap-2'>
                <Input
                  placeholder='할 일'
                  value={a.task ?? ''}
                  onChange={(e) => updateAction(i, { task: e.target.value })}
                />
                <Input
                  placeholder='담당'
                  className='w-24 shrink-0'
                  value={a.owner ?? ''}
                  onChange={(e) => updateAction(i, { owner: e.target.value })}
                />
                <Input
                  placeholder='기한'
                  className='w-24 shrink-0'
                  value={a.due ?? ''}
                  onChange={(e) => updateAction(i, { due: e.target.value })}
                />
                <Button
                  type='button'
                  variant='ghost'
                  size='sm'
                  className='h-8 w-8 shrink-0 p-0'
                  onClick={() => setActionItems((prev) => prev.filter((_, idx) => idx !== i))}
                >
                  <Trash2 className='h-4 w-4' />
                </Button>
              </div>
            ))}
          </div>

          <div className='space-y-1.5'>
            <FieldLabel>요약</FieldLabel>
            <Textarea rows={4} value={summary} onChange={(e) => setSummary(e.target.value)} />
          </div>

          <div className='space-y-1.5'>
            <FieldLabel>다음 단계 (줄바꿈으로 구분)</FieldLabel>
            <Textarea rows={2} value={nextSteps} onChange={(e) => setNextSteps(e.target.value)} />
          </div>
        </div>
      </div>

      <div className='flex justify-end gap-2 border-t p-3'>
        <Button variant='outline' size='sm' onClick={onCancel} disabled={saving}>
          취소
        </Button>
        <Button size='sm' onClick={handleSave} disabled={saving}>
          {saving ? '저장 중…' : '저장'}
        </Button>
      </div>
    </div>
  )
}
