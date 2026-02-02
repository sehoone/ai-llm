import { create } from 'zustand'
import { getCookie, setCookie, removeCookie } from '@/lib/cookies'

const ACCESS_TOKEN = 'access_token'
const REFRESH_TOKEN = 'refresh_token'
const EXPIRES_AT = 'expires_at'

interface AuthUser {
  accountNo: string
  email: string
  role: string[]
  exp: number
}

interface AuthState {
  auth: {
    user: AuthUser | null
    setUser: (user: AuthUser | null) => void
    accessToken: string
    refreshToken: string
    expiresAt: string | null
    setAccessToken: (accessToken: string) => void
    setRefreshToken: (refreshToken: string) => void
    setExpiresAt: (expiresAt: string) => void
    resetAccessToken: () => void
    reset: () => void
  }
}

export const useAuthStore = create<AuthState>()((set) => {
  const initToken = typeof window !== 'undefined' ? getCookie(ACCESS_TOKEN) || '' : ''
  const initRefreshToken = typeof window !== 'undefined' ? getCookie(REFRESH_TOKEN) || '' : ''
  const initExpiresAt = typeof window !== 'undefined' ? getCookie(EXPIRES_AT) || '' : ''

  return {
    auth: {
      user: null,
      setUser: (user) =>
        set((state) => ({ ...state, auth: { ...state.auth, user } })),
      accessToken: initToken,
      refreshToken: initRefreshToken,
      expiresAt: initExpiresAt,
      setAccessToken: (accessToken) =>
        set((state) => {
          if (typeof window !== 'undefined') {
            setCookie(ACCESS_TOKEN, accessToken)
          }
          return { ...state, auth: { ...state.auth, accessToken } }
        }),
      setRefreshToken: (refreshToken) =>
        set((state) => {
          if (typeof window !== 'undefined') {
            setCookie(REFRESH_TOKEN, refreshToken)
          }
          return { ...state, auth: { ...state.auth, refreshToken } }
        }),
      setExpiresAt: (expiresAt) =>
        set((state) => {
          if (typeof window !== 'undefined') {
            setCookie(EXPIRES_AT, expiresAt)
          }
          return { ...state, auth: { ...state.auth, expiresAt } }
        }),
      resetAccessToken: () =>
        set((state) => {
          if (typeof window !== 'undefined') {
            removeCookie(ACCESS_TOKEN)
          }
          return { ...state, auth: { ...state.auth, accessToken: '' } }
        }),
      reset: () =>
        set((state) => {
          if (typeof window !== 'undefined') {
            removeCookie(ACCESS_TOKEN)
            removeCookie(REFRESH_TOKEN)
            removeCookie(EXPIRES_AT)
          }
          return {
            ...state,
            auth: { ...state.auth, user: null, accessToken: '', refreshToken: '', expiresAt: null },
          }
        }),
    },
  }
})
