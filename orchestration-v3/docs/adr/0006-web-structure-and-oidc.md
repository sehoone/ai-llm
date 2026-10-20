# ADR-0006: 프론트 구조(shadcn-admin) 및 OIDC 리다이렉트 인증

- 상태: Accepted
- 날짜: 2026-10-17
- 결정자: sehoon
- 관련: [ADR-0003](0003-single-python-backend.md) (인증 IdP 위임), [ADR-0004](0004-apps-packages-monorepo-layout.md) (web 레이아웃 — FSD 표기 개정)

## Context (맥락)

V2 `admin-front`의 화면 전체를 V3 `apps/web`으로 이식해야 한다. 그런데 기존 V3 문서는
프론트를 **FSD(app/features/entities/shared)** 로 표방했고, V2 `admin-front`는 **shadcn-admin
템플릿 구조**(`src/{api,app,components,features,hooks,stores,context,lib,config,types,utils}`)라
둘이 다르다. 또한 V2는 **자체 로그인 화면·JWT 쿠키·토큰 refresh 인터셉터**를 앱이 소유하는데,
이는 **ADR-0003의 "인증은 사내 IdP(OIDC)에 위임, 앱은 발급·세션 비소유"** 와 정면 충돌한다.

두 가지를 결정해야 했다: ① 이식 시 구조(FSD 리팩터 vs shadcn-admin 유지), ② 인증 처리.

## Decision (결정)

### 1. 프론트 구조는 shadcn-admin 유지 (FSD 표방 철회)

- V2 `admin-front`는 20+ 기능을 가진 성숙한 shadcn-admin 앱이다. **FSD로 재배치하면 대수술·고위험**이고
  이식의 본질(화면 가져오기)과 무관하다. → **기존 구조를 그대로 유지**한다.
- ADR-0003/0004 문서의 "FSD" 표기는 골격 단계 희망사항이었고, 본 ADR로 **shadcn-admin 레이아웃으로 개정**한다.

```
apps/web/src/
├─ api/         # axios 인스턴스 + 도메인별 호출 (수작성)
├─ app/         # Next.js App Router — (authenticated)/ (errors)/ login/ auth/callback/
├─ features/    # 기능 폴더 (chats agents workflows meeting-minutes users …)
├─ components/  # ui(shadcn)·layout·data-table 공용
├─ hooks/ stores/ context/ lib/ config/ types/ utils/ styles/ assets/
```

- 계약(OpenAPI→TS)은 **보조 수단**으로 남긴다: `pnpm gen:types` → `src/types/api-schema.d.ts`.
  주 계약 메커니즘은 수작성 axios API 레이어(`src/api/*.ts`)다.

### 2. 인증은 OIDC Authorization Code + PKCE 리다이렉트 (ADR-0003 준수)

V2의 로그인/회원가입/OTP 화면과 토큰 refresh 큐를 **제거**하고 IdP 위임 플로우로 대체한다.

- **제거**: `app/(auth)/` 라우트 그룹, `features/auth/*`, axios의 refresh 큐·선제 갱신(`refreshAccessToken`).
- **추가**: `lib/oidc.ts` (discovery + PKCE), `/login`(authorize 리다이렉트), `/auth/callback`(code→token 교환).
- **auth-store**: access/id token 보관 + 표시용 클레임 디코드(검증 아님 — 권위는 백엔드 JWKS).
- **axios**: access token을 Bearer로 첨부, `ApiResponse<T>` 자동 unwrap, **401 → IdP 재로그인**(refresh 자작 없음).
- **로그아웃**: IdP `end_session_endpoint` 있으면 그쪽, 없으면 로컬 토큰 삭제 후 `/login`.
- 설정: `NEXT_PUBLIC_OIDC_{AUTHORITY,CLIENT_ID,SCOPE,REDIRECT_URI}`. 엔드포인트는 `.well-known` discovery로 해석.

### 3. 이식 범위

전체 화면 일괄 포팅. 단, 각 `src/api/*.ts`의 엔드포인트는 V2 백엔드 기준이므로 **V3 계약(`/api/v1/*`,
`ApiResponse` 래퍼)으로의 재매핑은 해당 백엔드 도메인 이식과 함께 후속**으로 진행한다(아래).

## Alternatives considered (대안)

| 대안 | 장점 | 기각 사유 |
|------|------|-----------|
| **FSD로 리팩터하며 이식** | V3 문서와 일치, 레이어 경계 선명 | 성숙한 20+ 기능 앱 대수술 — 고위험·고공수, 이식 본질과 무관. |
| **shadcn-admin 유지** (채택) | 검증된 구조, 이식 리스크 최소 | FSD 표방 철회 필요(본 ADR로 처리). |
| **V2 쿠키/로그인 임시 유지** | 즉시 동작 | ADR-0003 위배 상태로 머묾 — 기술부채. |
| **OIDC 리다이렉트 + PKCE** (채택) | IdP 위임 원칙 준수, 앱이 비밀 비보유 | 실제 IdP 설정·브라우저 검증 필요(스캐폴드). |

## Consequences (결과)

**긍정**
- 화면 자산 전부 확보, 이식 리스크 최소(구조 보존).
- 인증이 ADR-0003 원칙과 정렬 — 앱은 토큰 보관·첨부만, 발급·세션은 IdP.
- refresh 큐 제거로 axios 인증부가 대폭 단순화.

**부정 / 리스크**
- V3 문서의 FSD 방향 철회(일관성 위해 ADR-0003/0004 표기 개정).
- OIDC 플로우는 **스캐폴드** — 실제 IdP authority/client-id 주입과 브라우저 E2E 검증 전까지 미완.
- `src/api/*.ts`가 아직 V2 엔드포인트 기준 — **백엔드 도메인 이식 전까지 다수 화면이 미동작**.

**후속 작업**
- `pnpm install` + `pnpm build`로 타입·빌드 검증(Claude 셸에 pnpm 없음 — 사용자 실행).
- IdP 등록(공개 SPA 클라이언트, redirect_uri=`/auth/callback`) + `.env` OIDC 값 주입 + 로그인 E2E.
- 백엔드 도메인 이식과 함께 `src/api/*.ts` → `/api/v1/*`·`ApiResponse` 재매핑.
- (선택) 평가 기능 WebSocket/STT·TTS 의존성 재확인.
