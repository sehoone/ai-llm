import pino from 'pino';

/**
 * 로깅 유틸리티 (pino 사용)
 * 개발 환경(development)에서는 debug 레벨까지 출력하고,
 * 운영 환경(production)에서는 warn 이상의 로그만 출력합니다.
 */

const isProduction = process.env.NODE_ENV === 'production';

const pinoLogger = pino({
  level: isProduction ? 'warn' : 'debug',
  browser: {
    asObject: true, // 브라우저 콘솔에서 객체를 보기 좋게 출력
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

// 기존 Logger 인터페이스 호환을 위한 래퍼
class Logger {
  debug = (...args: unknown[]) => {
    pinoLogger.debug(this.formatArgs(args));
  };

  log = (...args: unknown[]) => {
    // pino에는 'log' 레벨이 없으므로 'info'로 매핑하거나 'debug'로 매핑
    pinoLogger.info(this.formatArgs(args));
  };

  info = (...args: unknown[]) => {
    pinoLogger.info(this.formatArgs(args));
  };

  warn = (...args: unknown[]) => {
    pinoLogger.warn(this.formatArgs(args));
  };

  error = (...args: unknown[]) => {
    pinoLogger.error(this.formatArgs(args));
  };

  // 여러 인자를 하나의 객체나 메시지로 변환
  private formatArgs = (args: unknown[]) => {
    if (args.length === 0) return undefined;
    if (args.length === 1) {
      return args[0];
    }
    return args; // pino will handle array or we can merge it
  }
}

export const logger = new Logger();
