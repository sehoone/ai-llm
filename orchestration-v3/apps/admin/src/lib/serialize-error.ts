import { isAxiosError } from 'axios'

/**
 * 에러 → 로그에 남길 최소 필드로 축약한다.
 * AxiosError는 config/request/response 트리 전체(잡음)를 버리고 유용한 값만 추린다.
 * logger가 항상 이 함수를 거치므로 "로그로 남길 에러의 모양"은 여기 한 곳에서 정의된다.
 */
export function serializeError(err: unknown): unknown {
  if (isAxiosError(err)) {
    const data = err.response?.data
    const detail =
      data && typeof data === 'object' && 'message' in data
        ? (data as { message?: string }).message
        : typeof data === 'string'
          ? data
          : undefined
    return {
      kind: 'http',
      method: err.config?.method?.toUpperCase(),
      url: err.config?.url,
      status: err.response?.status,
      // 백엔드 ApiResponse면 message, 평문이면 원문. 둘 다 없으면 axios 메시지.
      detail: detail ?? err.message,
    }
  }
  if (err instanceof Error) {
    return { kind: 'error', name: err.name, message: err.message, stack: err.stack }
  }
  // 일반 객체는 값 한 단계만 훑어 중첩 에러를 축약한다 (예: logger.error({ err }, '...')).
  if (err && typeof err === 'object' && !Array.isArray(err)) {
    const out: Record<string, unknown> = {}
    for (const [k, v] of Object.entries(err)) {
      out[k] = isAxiosError(v) || v instanceof Error ? serializeError(v) : v
    }
    return out
  }
  return err // 원시값/배열은 그대로
}
