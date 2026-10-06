import type { MinutesContent } from '@/api/meetings'
import { ScrollArea } from '@/components/ui/scroll-area'

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className='space-y-2'>
      <h3 className='text-sm font-semibold text-muted-foreground'>{title}</h3>
      {children}
    </div>
  )
}

export function MinutesPanel({ content }: { content: MinutesContent }) {
  const {
    attendees = [],
    agenda = [],
    discussion = [],
    decisions = [],
    action_items = [],
    summary,
    next_steps = [],
  } = content

  return (
    <ScrollArea className='h-[calc(100vh-16rem)]'>
      <div className='space-y-6 p-4'>
        {attendees.length > 0 && (
          <Section title='참석자'>
            <div className='flex flex-wrap gap-1.5'>
              {attendees.map((a, i) => (
                <span key={i} className='rounded-full bg-muted px-2.5 py-0.5 text-sm'>
                  {a}
                </span>
              ))}
            </div>
          </Section>
        )}

        {agenda.length > 0 && (
          <Section title='안건'>
            <ol className='list-inside list-decimal space-y-1 text-sm'>
              {agenda.map((a, i) => (
                <li key={i}>{a}</li>
              ))}
            </ol>
          </Section>
        )}

        {discussion.length > 0 && (
          <Section title='논의 내용'>
            <div className='space-y-3'>
              {discussion.map((d, i) => (
                <div key={i} className='space-y-1'>
                  <p className='text-sm font-medium'>{d.topic}</p>
                  {(d.points ?? []).length > 0 && (
                    <ul className='list-inside list-disc space-y-0.5 pl-2 text-sm text-muted-foreground'>
                      {(d.points ?? []).map((p, j) => (
                        <li key={j}>{p}</li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          </Section>
        )}

        {decisions.length > 0 && (
          <Section title='결정 사항'>
            <ul className='list-inside list-disc space-y-1 text-sm'>
              {decisions.map((d, i) => (
                <li key={i}>{d}</li>
              ))}
            </ul>
          </Section>
        )}

        {action_items.length > 0 && (
          <Section title='액션 아이템'>
            <ul className='space-y-1.5 text-sm'>
              {action_items.map((a, i) => (
                <li key={i} className='flex items-start gap-2'>
                  <input type='checkbox' disabled className='mt-1' />
                  <span>
                    {a.task}
                    {(a.owner || a.due) && (
                      <span className='text-muted-foreground'>
                        {' '}
                        ({a.owner}
                        {a.due ? `, ${a.due}` : ''})
                      </span>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          </Section>
        )}

        {summary && (
          <Section title='요약'>
            <p className='whitespace-pre-wrap text-sm leading-relaxed'>{summary}</p>
          </Section>
        )}

        {next_steps.length > 0 && (
          <Section title='다음 단계'>
            <ul className='list-inside list-disc space-y-1 text-sm'>
              {next_steps.map((n, i) => (
                <li key={i}>{n}</li>
              ))}
            </ul>
          </Section>
        )}
      </div>
    </ScrollArea>
  )
}
