import axios from 'axios'
import { toast } from 'sonner'
import { useAuthStore } from '@/stores/auth-store'

// 단일 백엔드(ADR-0003) — 모든 호출은 /api 로. next.config rewrite가 API_URL로 프록시.
const api = axios.create({
  baseURL: `${process.env.NEXT_PUBLIC_API_URL || ''}/api/`,
  headers: {
    'Content-Type': 'application/json',
  },
})

let redirecting = false

/** 토큰 만료/무효 → 로그인 페이지로 이동. refresh 자작 없음 — 재로그인. */
function reauthenticate() {
  if (redirecting || typeof window === 'undefined') return
  redirecting = true
  useAuthStore.getState().auth.reset()
  toast.error('인증이 만료되었습니다. 다시 로그인하세요.')
  const redirect = encodeURIComponent(window.location.pathname + window.location.search)
  window.location.href = `/login?redirect=${redirect}`
}

// 요청: access token을 Bearer로 첨부
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().auth.accessToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 응답: 백엔드 ApiResponse<T> 래퍼 { success, data } 자동 unwrap, 401 → 재로그인
api.interceptors.response.use(
  (response) => {
    if (
      response.data &&
      typeof response.data.success === 'boolean' &&
      'data' in response.data
    ) {
      response.data = response.data.data
    }
    return response
  },
  (error) => {
    if (error.response?.status === 401) {
      reauthenticate()
    }
    return Promise.reject(error)
  }
)

export default api
