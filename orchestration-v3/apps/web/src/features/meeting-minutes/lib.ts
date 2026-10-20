import type { MeetingStatus } from '@/api/meetings'

const TERMINAL_STATUSES: MeetingStatus[] = ['COMPLETED', 'SAVED', 'FAILED']

export function isProcessing(status: MeetingStatus): boolean {
  return !TERMINAL_STATUSES.includes(status)
}

export const STATUS_LABEL: Record<MeetingStatus, string> = {
  UPLOADED: '업로드됨',
  TRANSCRIBING: '전사 중',
  TRANSCRIBED: '전사 완료',
  SUMMARIZING: '요약 중',
  COMPLETED: '완료',
  SAVED: '저장됨',
  FAILED: '실패',
}

export function formatDuration(sec?: number | null): string {
  if (!sec || sec <= 0) return '—'
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

export function formatTimestamp(ms: number): string {
  const totalSec = Math.floor(ms / 1000)
  const m = Math.floor(totalSec / 60)
  const s = totalSec % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

// Stable color per speaker label (for timeline chips).
const SPEAKER_COLORS = [
  'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200',
  'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200',
  'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-200',
  'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200',
  'bg-pink-100 text-pink-800 dark:bg-pink-900/40 dark:text-pink-200',
  'bg-teal-100 text-teal-800 dark:bg-teal-900/40 dark:text-teal-200',
]

export function speakerColor(label: string): string {
  let hash = 0
  for (let i = 0; i < label.length; i++) hash = (hash * 31 + label.charCodeAt(i)) >>> 0
  return SPEAKER_COLORS[hash % SPEAKER_COLORS.length]
}
