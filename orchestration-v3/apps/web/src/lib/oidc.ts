/**
 * OIDC Authorization Code + PKCE 클라이언트 (공개 SPA 클라이언트).
 *
 * ADR-0003: 인증은 사내 IdP가 소유. 앱은 로그인 화면·세션을 자작하지 않는다 —
 * IdP authorize로 리다이렉트하고, 콜백에서 토큰을 받아 보관만 한다. 백엔드는 JWKS로 검증만.
 *
 * 설정은 env(`NEXT_PUBLIC_OIDC_*`). 엔드포인트는 discovery(.well-known)로 자동 해석.
 * ⚠️ 실제 IdP authority/client-id 주입 + 브라우저 검증 필요(스캐폴드).
 */
import { logger } from '@/lib/logger'

const AUTHORITY = process.env.NEXT_PUBLIC_OIDC_AUTHORITY || ''
const CLIENT_ID = process.env.NEXT_PUBLIC_OIDC_CLIENT_ID || ''
const SCOPE = process.env.NEXT_PUBLIC_OIDC_SCOPE || 'openid profile email'

const VERIFIER_KEY = 'oidc_code_verifier'
const STATE_KEY = 'oidc_state'
const RETURN_KEY = 'oidc_return_to'

function redirectUri(): string {
  if (process.env.NEXT_PUBLIC_OIDC_REDIRECT_URI) {
    return process.env.NEXT_PUBLIC_OIDC_REDIRECT_URI
  }
  return typeof window !== 'undefined' ? `${window.location.origin}/auth/callback` : ''
}

interface OidcConfig {
  authorization_endpoint: string
  token_endpoint: string
  end_session_endpoint?: string
}

let _config: OidcConfig | null = null

async function discover(): Promise<OidcConfig> {
  if (_config) return _config
  if (!AUTHORITY) throw new Error('NEXT_PUBLIC_OIDC_AUTHORITY가 설정되지 않았습니다.')
  const res = await fetch(`${AUTHORITY.replace(/\/$/, '')}/.well-known/openid-configuration`)
  if (!res.ok) throw new Error(`OIDC discovery 실패: ${res.status}`)
  _config = (await res.json()) as OidcConfig
  return _config
}

// ── PKCE 헬퍼 ──────────────────────────────────────────────
function base64url(bytes: ArrayBuffer): string {
  return btoa(String.fromCharCode(...new Uint8Array(bytes)))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '')
}

function randomString(len = 64): string {
  const arr = new Uint8Array(len)
  crypto.getRandomValues(arr)
  return base64url(arr.buffer)
}

async function sha256(input: string): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(input))
  return base64url(digest)
}

/** IdP authorize로 리다이렉트 (PKCE verifier/state를 세션에 보관). */
export async function beginLogin(returnTo?: string): Promise<void> {
  const cfg = await discover()
  const verifier = randomString()
  const challenge = await sha256(verifier)
  const state = randomString(16)

  sessionStorage.setItem(VERIFIER_KEY, verifier)
  sessionStorage.setItem(STATE_KEY, state)
  if (returnTo) sessionStorage.setItem(RETURN_KEY, returnTo)

  const params = new URLSearchParams({
    response_type: 'code',
    client_id: CLIENT_ID,
    redirect_uri: redirectUri(),
    scope: SCOPE,
    state,
    code_challenge: challenge,
    code_challenge_method: 'S256',
  })
  window.location.href = `${cfg.authorization_endpoint}?${params.toString()}`
}

export interface TokenResult {
  accessToken: string
  idToken?: string
  refreshToken?: string
  returnTo: string
}

/** 콜백: code→token 교환(verifier 사용). state 검증 후 토큰 반환. */
export async function completeLogin(): Promise<TokenResult> {
  const url = new URL(window.location.href)
  const code = url.searchParams.get('code')
  const state = url.searchParams.get('state')
  const verifier = sessionStorage.getItem(VERIFIER_KEY)
  const savedState = sessionStorage.getItem(STATE_KEY)
  const returnTo = sessionStorage.getItem(RETURN_KEY) || '/'

  sessionStorage.removeItem(VERIFIER_KEY)
  sessionStorage.removeItem(STATE_KEY)
  sessionStorage.removeItem(RETURN_KEY)

  if (!code || !verifier) throw new Error('인가 코드 또는 PKCE verifier 없음')
  if (state !== savedState) throw new Error('OIDC state 불일치 (CSRF 의심)')

  const cfg = await discover()
  const body = new URLSearchParams({
    grant_type: 'authorization_code',
    code,
    client_id: CLIENT_ID,
    redirect_uri: redirectUri(),
    code_verifier: verifier,
  })
  const res = await fetch(cfg.token_endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  })
  if (!res.ok) {
    logger.error({ status: res.status }, 'OIDC 토큰 교환 실패')
    throw new Error(`토큰 교환 실패: ${res.status}`)
  }
  const data = await res.json()
  return {
    accessToken: data.access_token,
    idToken: data.id_token,
    refreshToken: data.refresh_token,
    returnTo,
  }
}

/** IdP 세션 종료 URL (있으면). 없으면 null → 로컬 로그아웃만. */
export async function buildLogoutUrl(idToken?: string): Promise<string | null> {
  try {
    const cfg = await discover()
    if (!cfg.end_session_endpoint) return null
    const params = new URLSearchParams({
      post_logout_redirect_uri: typeof window !== 'undefined' ? window.location.origin : '',
    })
    if (idToken) params.set('id_token_hint', idToken)
    return `${cfg.end_session_endpoint}?${params.toString()}`
  } catch {
    return null
  }
}
