import { logger } from '@/lib/logger'

/**
 * Creates an onDownloadProgress handler that parses 'data: {json}\n\n' SSE streams.
 * Returns { onDownloadProgress, flush } — call flush() after the request resolves
 * to process any trailing bytes that didn't end with \n\n.
 */
export function createSSEProgressHandler<T>(onChunk: (data: T) => void): {
  onDownloadProgress: (progressEvent: { event?: { target?: unknown } }) => void
  flush: () => void
} {
  let buffer = ''
  let processedIndex = 0

  const emit = (part: string, suppressErrors = false) => {
    const line = part.trim()
    if (!line.startsWith('data: ')) return
    const dataStr = line.slice(6)
    if (dataStr === '[DONE]') return
    try {
      onChunk(JSON.parse(dataStr) as T)
    } catch (e) {
      if (!suppressErrors) logger.error('SSE parse error', e, 'chunk:', dataStr)
    }
  }

  return {
    onDownloadProgress(progressEvent) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const xhr = progressEvent.event?.target as any
      if (!xhr) return
      const responseText: string = xhr.responseText || ''
      const newContent = responseText.substring(processedIndex)
      processedIndex = responseText.length
      buffer += newContent
      const parts = buffer.split('\n\n')
      buffer = parts.pop() ?? ''
      for (const part of parts) emit(part)
    },
    flush() {
      if (!buffer.trim()) return
      for (const part of buffer.split('\n\n')) emit(part, true)
    },
  }
}

/**
 * Creates an onDownloadProgress handler for event-framed SSE streams
 * (`event: <name>\ndata: <json>\n\n`). Dispatches each frame by its event name.
 * Frames without an explicit `event:` line are reported as event 'message'.
 * Call flush() after the request resolves to drain any trailing frame.
 */
export function createEventSSEHandler(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onEvent: (event: string, data: any) => void
): {
  onDownloadProgress: (progressEvent: { event?: { target?: unknown } }) => void
  flush: () => void
} {
  let buffer = ''
  let processedIndex = 0

  const emit = (frame: string, suppressErrors = false) => {
    let event = 'message'
    const dataLines: string[] = []
    for (const raw of frame.split('\n')) {
      const line = raw.trimEnd()
      if (line.startsWith('event:')) event = line.slice(6).trim()
      else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
    }
    if (dataLines.length === 0) return
    const dataStr = dataLines.join('\n')
    if (dataStr === '[DONE]') return
    try {
      onEvent(event, JSON.parse(dataStr))
    } catch (e) {
      if (!suppressErrors) logger.error('SSE parse error', e, 'frame:', frame)
    }
  }

  return {
    onDownloadProgress(progressEvent) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const xhr = progressEvent.event?.target as any
      if (!xhr) return
      const responseText: string = xhr.responseText || ''
      const newContent = responseText.substring(processedIndex)
      processedIndex = responseText.length
      buffer += newContent
      const frames = buffer.split('\n\n')
      buffer = frames.pop() ?? ''
      for (const frame of frames) if (frame.trim()) emit(frame)
    },
    flush() {
      if (!buffer.trim()) return
      for (const frame of buffer.split('\n\n')) if (frame.trim()) emit(frame, true)
    },
  }
}

/**
 * Creates an onDownloadProgress handler that parses newline-delimited JSON streams.
 * Each line is a complete JSON object (no 'data:' prefix).
 */
export function createNDJSONProgressHandler<T>(onChunk: (data: T) => void): {
  onDownloadProgress: (progressEvent: { event?: { target?: unknown } }) => void
} {
  let buffer = ''
  let processedIndex = 0

  return {
    onDownloadProgress(progressEvent) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const xhr = progressEvent.event?.target as any
      if (!xhr) return
      const responseText: string = xhr.responseText || xhr.response || ''
      const newContent = responseText.substring(processedIndex)
      processedIndex = responseText.length
      buffer += newContent
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''
      for (const line of lines) {
        if (!line.trim()) continue
        try {
          onChunk(JSON.parse(line) as T)
        } catch (e) {
          logger.error('NDJSON parse error', e)
        }
      }
    },
  }
}
