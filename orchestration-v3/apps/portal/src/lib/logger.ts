import { serializeError } from '@/lib/serialize-error'

/**
 * 로깅 유틸리티 (console 기반 — portal은 린 구성이라 pino 미사용).
 * admin(apps/admin)의 logger와 동일한 출력을 목표로 한다:
 *   [시각] 메시지 { ...축약된 필드 }
 * 개발 환경에서는 debug 레벨까지, 운영 환경에서는 warn 이상만 출력한다.
 * 모든 인자는 serializeError를 거치므로 AxiosError/Error를 통째로 넘겨도 요약된다.
 */

const isProduction = process.env.NODE_ENV === 'production'

type Level = 'debug' | 'info' | 'warn' | 'error'

const LEVEL_ORDER: Record<Level, number> = { debug: 20, info: 30, warn: 40, error: 50 }
const MIN_LEVEL = isProduction ? LEVEL_ORDER.warn : LEVEL_ORDER.debug

class Logger {
  debug = (...args: unknown[]) => this.emit('debug', args)

  // console에는 'log'도 있으나 레벨 매핑 일관성을 위해 info로 통일
  log = (...args: unknown[]) => this.emit('info', args)

  info = (...args: unknown[]) => this.emit('info', args)

  warn = (...args: unknown[]) => this.emit('warn', args)

  error = (...args: unknown[]) => this.emit('error', args)

  private emit = (level: Level, args: unknown[]) => {
    if (LEVEL_ORDER[level] < MIN_LEVEL) return

    // 첫 인자가 문자열이면 메시지로, 나머지는 메타로. (logger.error('msg', err) 패턴)
    let message = ''
    let rest = args
    if (typeof args[0] === 'string') {
      message = args[0]
      rest = args.slice(1)
    }

    const ts = new Date().toLocaleTimeString()
    const prefix = `[${ts}]${message ? ` ${message}` : ''}`
    const meta = this.toMeta(rest)

    if (meta === undefined) {
      console[level](prefix)
    } else {
      console[level](prefix, meta)
    }
  }

  // 나머지 인자들을 serializeError로 축약한다.
  private toMeta = (rest: unknown[]): unknown => {
    if (rest.length === 0) return undefined
    if (rest.length === 1) return serializeError(rest[0])
    return { args: rest.map(serializeError) }
  }
}

export const logger = new Logger()
