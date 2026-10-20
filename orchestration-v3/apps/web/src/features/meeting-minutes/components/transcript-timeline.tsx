import type { Segment } from '@/api/meetings'
import { ScrollArea } from '@/components/ui/scroll-area'
import { formatTimestamp, speakerColor } from '../lib'

export function TranscriptTimeline({ segments }: { segments: Segment[] }) {
  if (segments.length === 0) {
    return <p className='p-4 text-sm text-muted-foreground'>전사 내용이 없습니다.</p>
  }
  return (
    <ScrollArea className='h-[calc(100vh-16rem)]'>
      <div className='space-y-4 p-4'>
        {segments.map((s) => {
          const speaker = s.speaker_name || s.speaker_label
          return (
            <div key={s.seq} className='space-y-1'>
              <div className='flex items-center gap-2'>
                <span className={`rounded px-2 py-0.5 text-xs font-medium ${speakerColor(s.speaker_label)}`}>
                  {speaker}
                </span>
                <span className='text-xs text-muted-foreground'>{formatTimestamp(s.start_ms)}</span>
              </div>
              <p className='text-sm leading-relaxed'>{s.text}</p>
            </div>
          )
        })}
      </div>
    </ScrollArea>
  )
}
