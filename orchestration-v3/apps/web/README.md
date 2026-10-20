# web

Next.js(TS) 관리자 UI. V2 `admin-front`(shadcn-admin 기반)에서 이식 (ADR-0006).

## 구조 (shadcn-admin, FSD 아님 — ADR-0006)

```
src/
├─ api/         # axios 인스턴스 + 도메인별 호출 (수작성)
├─ app/         # Next.js App Router — (authenticated)/ (errors)/ login/ auth/callback/
├─ features/    # 기능 단위 (chats, agents, workflows, meeting-minutes, users …)
├─ components/  # ui(shadcn)·layout·data-table 등 공용
├─ hooks/ stores/ context/ lib/ config/ types/ utils/ styles/ assets/
```

## 인증 (ADR-0003 / ADR-0006)

자체 로그인 화면 없음 — 사내 IdP(OIDC)에 위임.

- `/login` → `lib/oidc.ts`의 `beginLogin()`으로 IdP authorize 리다이렉트 (Authorization Code + PKCE).
- `/auth/callback` → `completeLogin()`으로 code→token 교환, `auth-store`에 저장 후 복귀.
- `api/axios.ts` → access token을 Bearer로 첨부, 401 시 IdP 재로그인(refresh 자작 없음).
- 설정: `.env`의 `NEXT_PUBLIC_OIDC_*`. 엔드포인트는 discovery(`.well-known`)로 자동 해석.

## 개발

```bash
pnpm install
cp .env.example .env     # NEXT_PUBLIC_API_URL + NEXT_PUBLIC_OIDC_* 채우기
pnpm dev                 # :3000
pnpm build && pnpm start
pnpm lint
pnpm gen:types           # 백엔드 OpenAPI → src/types/api-schema.d.ts (보조)
```

> ⚠️ 포팅 직후 상태. 검증 필요: 의존성 설치·빌드, IdP 실제 값 주입, 그리고 API 경로를
> V3 백엔드(`/api/v1/*`, `ApiResponse` 래퍼) 계약에 맞게 `src/api/*.ts` 재매핑
> (백엔드 도메인 이식과 함께 진행).
