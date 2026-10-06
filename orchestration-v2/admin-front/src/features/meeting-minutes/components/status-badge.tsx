import { Badge } from '@/components/ui/badge'
import type { MeetingStatus } from '@/api/meetings'
import { STATUS_LABEL, isProcessing } from '../lib'

const VARIANT: Record<MeetingStatus, string> = {
  UPLOADED: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200',
  TRANSCRIBING: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-200',
  TRANSCRIBED: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-200',
  SUMMARIZING: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-200',
  COMPLETED: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-200',
  SAVED: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-200',
  FAILED: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-200',
}

export function StatusBadge({ status }: { status: MeetingStatus }) {
  const processing = isProcessing(status)
  return (
    <Badge variant='secondary' className={VARIANT[status]}>
      {processing && (
        <span className='mr-1.5 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-current' />
      )}
      {STATUS_LABEL[status]}
    </Badge>
  )
}
