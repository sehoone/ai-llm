// 쿠키 유틸 (web과 동일 패턴) — JWT access token 보관용. 의존성 없이 document.cookie 직접 조작.

const DEFAULT_MAX_AGE = 60 * 60 * 24 * 7; // 7일

export function getCookie(name: string): string | undefined {
  if (typeof document === 'undefined') return undefined;
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return parts.pop()?.split(';').shift();
  }
  return undefined;
}

export function setCookie(name: string, value: string, maxAge: number = DEFAULT_MAX_AGE): void {
  if (typeof document === 'undefined') return;
  document.cookie = `${name}=${value}; path=/; max-age=${maxAge}`;
}

export function removeCookie(name: string): void {
  if (typeof document === 'undefined') return;
  document.cookie = `${name}=; path=/; max-age=0`;
}
