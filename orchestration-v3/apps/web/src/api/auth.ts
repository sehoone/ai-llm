// ADR-0003: 앱은 로그인/토큰 발급을 소유하지 않는다. 전부 IdP(OIDC) 위임.
// 로그인·콜백·로그아웃은 lib/oidc.ts의 리다이렉트 플로우를 사용한다.
export { beginLogin, completeLogin, buildLogoutUrl } from '@/lib/oidc'
export type { TokenResult } from '@/lib/oidc'
