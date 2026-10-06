import { create } from 'zustand'
import { logger } from '@/lib/logger'
import { idbAddChunk, idbClear, idbGetChunks, idbGetMeta, idbSetMeta } from '@/lib/recorder-idb'

export type RecorderStatus = 'idle' | 'recording' | 'paused' | 'stopped'

const MIME = 'audio/webm'
const TIMESLICE_MS = 5000 // emit a chunk every 5s → periodic IndexedDB persistence

interface RecorderState {
  status: RecorderStatus
  elapsedMs: number
  error: string | null
  blob: Blob | null
  blobUrl: string | null
  saveOpen: boolean // whether the global save dialog should be shown
  recovered: boolean // audio was restored from a previous session
  start: () => Promise<void>
  pause: () => void
  resume: () => void
  stop: () => void
  discard: () => void
  setSaveOpen: (open: boolean) => void
  recover: () => Promise<void>
}

// Non-reactive handles at module scope survive route changes without re-renders.
let mediaRecorder: MediaRecorder | null = null
let stream: MediaStream | null = null
let chunks: Blob[] = []
let intervalId: ReturnType<typeof setInterval> | null = null
let startedAt = 0
let accumulatedMs = 0
let recoverAttempted = false

function clearTimer() {
  if (intervalId) {
    clearInterval(intervalId)
    intervalId = null
  }
}

function stopStream() {
  if (stream) {
    stream.getTracks().forEach((t) => t.stop())
    stream = null
  }
}

function currentElapsed() {
  return accumulatedMs + (startedAt ? Date.now() - startedAt : 0)
}

export const useRecorderStore = create<RecorderState>((set, get) => ({
  status: 'idle',
  elapsedMs: 0,
  error: null,
  blob: null,
  blobUrl: null,
  saveOpen: false,
  recovered: false,

  start: async () => {
    if (get().status === 'recording' || get().status === 'paused') return

    if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
      set({
        error:
          typeof window !== 'undefined' && window.isSecureContext === false
            ? '보안 연결(HTTPS) 또는 localhost에서만 녹음할 수 있습니다. 파일 업로드를 이용하세요.'
            : '이 브라우저에서는 녹음을 사용할 수 없습니다. 파일 업로드를 이용하세요.',
      })
      return
    }

    const prevUrl = get().blobUrl
    if (prevUrl) URL.revokeObjectURL(prevUrl)
    await idbClear()

    try {
      const s = await navigator.mediaDevices.getUserMedia({ audio: true })
      stream = s
      chunks = []
      accumulatedMs = 0

      const mr = new MediaRecorder(s, { mimeType: 'audio/webm;codecs=opus' })
      mr.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunks.push(e.data)
          void idbAddChunk(e.data)
          void idbSetMeta({ status: 'recording', mimeType: MIME, elapsedMs: currentElapsed(), updatedAt: Date.now() })
        }
      }
      mr.onstop = () => {
        const blob = new Blob(chunks, { type: MIME })
        stopStream()
        void idbSetMeta({ status: 'stopped', mimeType: MIME, elapsedMs: accumulatedMs, updatedAt: Date.now() })
        set({ status: 'stopped', blob, blobUrl: URL.createObjectURL(blob), saveOpen: true })
      }
      mr.onerror = () => set({ error: '녹음 중 오류가 발생했습니다.' })
      mediaRecorder = mr
      mr.start(TIMESLICE_MS)

      startedAt = Date.now()
      clearTimer()
      intervalId = setInterval(() => set({ elapsedMs: currentElapsed() }), 250)

      void idbSetMeta({ status: 'recording', mimeType: MIME, elapsedMs: 0, updatedAt: Date.now() })
      set({ status: 'recording', elapsedMs: 0, error: null, blob: null, blobUrl: null, recovered: false })
    } catch (err) {
      logger.error('[recorder-store] start failed', err)
      const name = err instanceof DOMException ? err.name : ''
      set({
        error:
          name === 'NotAllowedError' || name === 'SecurityError'
            ? '마이크 권한이 거부되었습니다. 브라우저 사이트 설정에서 마이크를 허용해 주세요.'
            : name === 'NotFoundError' || name === 'DevicesNotFoundError'
              ? '사용 가능한 마이크를 찾을 수 없습니다.'
              : '마이크를 시작할 수 없습니다. 파일 업로드를 이용해 주세요.',
      })
      stopStream()
    }
  },

  pause: () => {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
      mediaRecorder.pause()
      accumulatedMs += Date.now() - startedAt
      startedAt = 0
      clearTimer()
      void idbSetMeta({ status: 'paused', mimeType: MIME, elapsedMs: accumulatedMs, updatedAt: Date.now() })
      set({ status: 'paused', elapsedMs: accumulatedMs })
    }
  },

  resume: () => {
    if (mediaRecorder && mediaRecorder.state === 'paused') {
      mediaRecorder.resume()
      startedAt = Date.now()
      clearTimer()
      intervalId = setInterval(() => set({ elapsedMs: currentElapsed() }), 250)
      set({ status: 'recording' })
    }
  },

  stop: () => {
    clearTimer()
    if (startedAt) {
      accumulatedMs += Date.now() - startedAt
      startedAt = 0
    }
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop() // onstop builds blob + sets status/saveOpen
    }
    mediaRecorder = null
  },

  discard: () => {
    clearTimer()
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      try {
        mediaRecorder.stop()
      } catch {
        // ignore
      }
    }
    mediaRecorder = null
    stopStream()
    chunks = []
    accumulatedMs = 0
    startedAt = 0
    const url = get().blobUrl
    if (url) URL.revokeObjectURL(url)
    void idbClear()
    set({ status: 'idle', elapsedMs: 0, error: null, blob: null, blobUrl: null, saveOpen: false, recovered: false })
  },

  setSaveOpen: (open: boolean) => set({ saveOpen: open }),

  recover: async () => {
    if (recoverAttempted) return
    recoverAttempted = true
    if (get().status !== 'idle') return
    const saved = await idbGetChunks()
    if (!saved.length) return
    const meta = await idbGetMeta()
    const blob = new Blob(saved, { type: meta?.mimeType || MIME })
    if (blob.size === 0) {
      await idbClear()
      return
    }
    accumulatedMs = meta?.elapsedMs || 0
    set({
      status: 'stopped',
      blob,
      blobUrl: URL.createObjectURL(blob),
      elapsedMs: meta?.elapsedMs || 0,
      saveOpen: true,
      recovered: true,
    })
    logger.debug('[recorder-store] recovered previous recording', { bytes: blob.size })
  },
}))
