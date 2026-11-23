'use client'

import { useMemo, useState } from 'react'
import { meetingApi, type Segment } from '@/api/meetings'
import { logger } from '@/lib/logger'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'

interface Props {
  meetingId: string
  segments: Segment[]
  open: boolean
  onOpenChange: (open: boolean) => void
  onSaved: () => void
}

export function SpeakerMappingDialog({ meetingId, segments, open, onOpenChange, onSaved }: Props) {
  const labels = useMemo(() => {
    const map = new Map<string, string>()
    for (const s of segments) {
      if (!map.has(s.speaker_label)) map.set(s.speaker_label, s.speaker_name || '')
    }
    return Array.from(map.entries())
  }, [segments])

  const [names, setNames] = useState<Record<string, string>>(() =>
    Object.fromEntries(labels.map(([label, name]) => [label, name]))
  )
  const [saving, setSaving] = useState(false)

  const save = async () => {
    const mapping: Record<string, string> = {}
    for (const [label, name] of Object.entries(names)) {
      if (name.trim()) mapping[label] = name.trim()
    }
    setSaving(true)
    try {
      await meetingApi.updateSpeakers(meetingId, mapping)
      toast.success('화자 매핑이 저장되었습니다.')
      onSaved()
      onOpenChange(false)
    } catch (error) {
      logger.error(error)
      toast.error('저장에 실패했습니다.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className='max-w-sm'>
        <DialogHeader>
          <DialogTitle>화자 지정</DialogTitle>
          <DialogDescription>각 화자 라벨에 실명을 지정합니다.</DialogDescription>
        </DialogHeader>
        <div className='space-y-3'>
          {labels.map(([label]) => (
            <div key={label} className='flex items-center gap-3'>
              <span className='w-24 shrink-0 text-sm text-muted-foreground'>{label}</span>
              <Input
                placeholder='실명'
                value={names[label] ?? ''}
                onChange={(e) => setNames((prev) => ({ ...prev, [label]: e.target.value }))}
              />
            </div>
          ))}
        </div>
        <DialogFooter>
          <Button variant='outline' onClick={() => onOpenChange(false)}>
            취소
          </Button>
          <Button onClick={save} disabled={saving}>
            {saving ? '저장 중…' : '저장'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
