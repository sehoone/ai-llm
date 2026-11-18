import { create } from 'zustand';
import { getCookie, removeCookie, setCookie } from '@/lib/cookies';

// 사용자 포털 인증(ADR-0009·0020): 백엔드가 ID/PW 검증 후 HS256 JWT 발급.
// 앱은 access token을 쿠키에 보관하고 Bearer로 첨부만 한다. refresh 자작 없음 — 만료/401 시 재로그인.
const ACCESS_TOKEN = 'access_token';

interface AuthUser {
  sub: string;
  email?: string;
  username?: string;
  roles: string[];
  exp?: number;
}

interface AuthState {
  auth: {
    user: AuthUser | null;
    accessToken: string;
    setSession: (accessToken: string) => void;
    reset: () => void;
  };
}

/** JWT payload 디코드(검증 아님 — 표시용. 권위는 백엔드). */
function decodeClaims(token: string): AuthUser | null {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    const rawRoles = payload.roles ?? payload.role ?? [];
    return {
      sub: payload.sub,
      email: payload.email,
      username: payload.preferred_username ?? payload.name ?? payload.username,
      roles: Array.isArray(rawRoles) ? rawRoles : [rawRoles].filter(Boolean),
      exp: payload.exp,
    };
  } catch {
    return null;
  }
}

export const useAuthStore = create<AuthState>()((set) => {
  const initToken = typeof window !== 'undefined' ? getCookie(ACCESS_TOKEN) || '' : '';

  return {
    auth: {
      user: initToken ? decodeClaims(initToken) : null,
      accessToken: initToken,
      setSession: (accessToken) =>
        set((state) => {
          if (typeof window !== 'undefined') setCookie(ACCESS_TOKEN, accessToken);
          return {
            ...state,
            auth: { ...state.auth, accessToken, user: decodeClaims(accessToken) },
          };
        }),
      reset: () =>
        set((state) => {
          if (typeof window !== 'undefined') removeCookie(ACCESS_TOKEN);
          return { ...state, auth: { ...state.auth, user: null, accessToken: '' } };
        }),
    },
  };
});
