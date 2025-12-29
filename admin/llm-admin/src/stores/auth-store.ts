import { create } from 'zustand'

const ACCESS_TOKEN = 'access_token'
const REFRESH_TOKEN = 'refresh_token'

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
    setAccessToken: (accessToken: string) => void
    setRefreshToken: (refreshToken: string) => void
    resetAccessToken: () => void
    reset: () => void
  }
}

export const useAuthStore = create<AuthState>()((set) => {
  const initToken = typeof window !== 'undefined' ? localStorage.getItem(ACCESS_TOKEN) || '' : ''
  const initRefreshToken = typeof window !== 'undefined' ? localStorage.getItem(REFRESH_TOKEN) || '' : ''

  return {
    auth: {
      user: null,
      setUser: (user) =>
        set((state) => ({ ...state, auth: { ...state.auth, user } })),
      accessToken: initToken,
      refreshToken: initRefreshToken,
      setAccessToken: (accessToken) =>
        set((state) => {
          if (typeof window !== 'undefined') {
            localStorage.setItem(ACCESS_TOKEN, accessToken)
          }
          return { ...state, auth: { ...state.auth, accessToken } }
        }),
      setRefreshToken: (refreshToken) =>
        set((state) => {
          if (typeof window !== 'undefined') {
            localStorage.setItem(REFRESH_TOKEN, refreshToken)
          }
          return { ...state, auth: { ...state.auth, refreshToken } }
        }),
      resetAccessToken: () =>
        set((state) => {
          if (typeof window !== 'undefined') {
            localStorage.removeItem(ACCESS_TOKEN)
          }
          return { ...state, auth: { ...state.auth, accessToken: '' } }
        }),
      reset: () =>
        set((state) => {
          if (typeof window !== 'undefined') {
            localStorage.removeItem(ACCESS_TOKEN)
            localStorage.removeItem(REFRESH_TOKEN)
          }
          return {
            ...state,
            auth: { ...state.auth, user: null, accessToken: '', refreshToken: '' },
          }
        }),
    },
  }
})
