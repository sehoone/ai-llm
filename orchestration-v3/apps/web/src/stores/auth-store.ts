import { create } from 'zustand'
import { getCookie, removeCookie, setCookie } from '@/lib/cookies'

// ADR-0003: 토큰은 IdP가 발급. 앱은 access token을 보관하고 Bearer로 첨부만 한다.
// refresh token 선제 갱신 로직 없음 — 만료/401 시 IdP로 재로그인(ADR-0005 프론트 인증).
const ACCESS_TOKEN = 'access_token'
const ID_TOKEN = 'id_token'

interface AuthUser {
  sub: string
  email?: string
  username?: string
  roles: string[]
  exp?: number
}

interface AuthState {
  auth: {
    user: AuthUser | null
    accessToken: string
    idToken: string
    setSession: (accessToken: string, idToken?: string) => void
    setUser: (user: AuthUser | null) => void
    reset: () => void
  }
}

/** JWT payload를 디코드(검증 아님 — 표시용. 권위는 백엔드 JWKS 검증). */
function decodeClaims(token: string): AuthUser | null {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    const rawRoles = payload.roles ?? payload.realm_access?.roles ?? []
    return {
      sub: payload.sub,
      email: payload.email,
      username: payload.preferred_username ?? payload.name,
      roles: Array.isArray(rawRoles) ? rawRoles : [rawRoles].filter(Boolean),
      exp: payload.exp,
    }
  } catch {
    return null
  }
}

export const useAuthStore = create<AuthState>()((set) => {
  const initToken = typeof window !== 'undefined' ? getCookie(ACCESS_TOKEN) || '' : ''
  const initIdToken = typeof window !== 'undefined' ? getCookie(ID_TOKEN) || '' : ''

  return {
    auth: {
      user: initToken ? decodeClaims(initToken) : null,
      accessToken: initToken,
      idToken: initIdToken,
      setSession: (accessToken, idToken) =>
        set((state) => {
          if (typeof window !== 'undefined') {
            setCookie(ACCESS_TOKEN, accessToken)
            if (idToken) setCookie(ID_TOKEN, idToken)
          }
          return {
            ...state,
            auth: {
              ...state.auth,
              accessToken,
              idToken: idToken ?? state.auth.idToken,
              user: decodeClaims(accessToken),
            },
          }
        }),
      setUser: (user) => set((state) => ({ ...state, auth: { ...state.auth, user } })),
      reset: () =>
        set((state) => {
          if (typeof window !== 'undefined') {
            removeCookie(ACCESS_TOKEN)
            removeCookie(ID_TOKEN)
          }
          return {
            ...state,
            auth: { ...state.auth, user: null, accessToken: '', idToken: '' },
          }
        }),
    },
  }
})
