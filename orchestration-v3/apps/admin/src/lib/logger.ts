import pino from 'pino';
import { serializeError } from '@/lib/serialize-error';

/**
 * 로깅 유틸리티 (pino 사용)
 * 개발 환경(development)에서는 debug 레벨까지 출력하고,
 * 운영 환경(production)에서는 warn 이상의 로그만 출력합니다.
 */

const isProduction = process.env.NODE_ENV === 'production';

// pino level 숫자 → console 메서드 (level 필드는 숨기되 색/심각도는 콘솔 메서드로 유지)
const LEVEL_TO_CONSOLE: Record<number, 'debug' | 'info' | 'warn' | 'error'> = {
  10: 'debug', // trace
  20: 'debug',
  30: 'info',
  40: 'warn',
  50: 'error',
  60: 'error', // fatal
};

/** 브라우저 콘솔 출력 포맷 — level 숨김, time은 읽기 쉬운 시각으로 변환. */
function writeToConsole(o: Record<string, unknown>) {
  const { level, time, msg, ...rest } = o;
  const method = LEVEL_TO_CONSOLE[level as number] ?? 'log';
  const ts = typeof time === 'number' ? new Date(time).toLocaleTimeString() : time;
  const prefix = `[${ts}]${msg ? ` ${msg}` : ''}`;
  if (Object.keys(rest).length > 0) {
    console[method](prefix, rest);
  } else {
    console[method](prefix);
  }
}

const pinoLogger = pino({
  level: isProduction ? 'warn' : 'debug',
  browser: {
    asObject: true, // write가 객체를 받도록
    write: writeToConsole,
  },
  // 서버 사이드에서 예쁘게 출력하려면 pino-pretty 등을 추가 설정할 수 있습니다.
  transport: !isProduction && typeof window === 'undefined'
    ? {
        target: 'pino-pretty',
        options: {
          colorize: true,
        },
      }
    : undefined,
});

type Level = 'debug' | 'info' | 'warn' | 'error';

// 기존 Logger 인터페이스 호환을 위한 래퍼.
// 모든 인자는 serializeError를 거치므로 AxiosError/Error를 통째로 넘겨도 요약된다.
// 가변 인자 유지 — logger.error('msg', err, 'chunk:', data) 같은 다중 인자 호출부 보존.
class Logger {
  debug = (...args: unknown[]) => this.emit('debug', args);

  // pino에는 'log' 레벨이 없으므로 'info'로 매핑
  log = (...args: unknown[]) => this.emit('info', args);

  info = (...args: unknown[]) => this.emit('info', args);

  warn = (...args: unknown[]) => this.emit('warn', args);

  error = (...args: unknown[]) => this.emit('error', args);

  private emit = (level: Level, args: unknown[]) => {
    if (args.length === 0) {
      pinoLogger[level]('');
      return;
    }

    // 첫 인자가 문자열이면 메시지로, 나머지는 메타로. (logger.error('msg', err) 패턴)
    if (typeof args[0] === 'string') {
      const message = args[0];
      const rest = args.slice(1);
      if (rest.length === 0) {
        pinoLogger[level](message);
      } else {
        pinoLogger[level](this.toMeta(rest), message);
      }
      return;
    }

    // 하위호환: logger.error(error) — 에러만 넘겨도 요약
    pinoLogger[level](this.toMeta(args));
  };

  // 나머지 인자들을 serializeError로 축약해 pino mergingObject(객체)로 만든다.
  private toMeta = (rest: unknown[]): object => {
    if (rest.length === 1) {
      const s = serializeError(rest[0]);
      return s !== null && typeof s === 'object' ? s : { value: s };
    }
    return { args: rest.map(serializeError) };
  };
}

export const logger = new Logger();
