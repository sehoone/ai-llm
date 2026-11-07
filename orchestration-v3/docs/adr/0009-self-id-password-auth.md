# ADR-0009: 자체 ID/PW 인증 (IdP 위임에서 전환)

- 상태: Accepted
- 날짜: 2026-11-07
- 결정자: sehoon
- 관련: [ADR-0003](0003-single-python-backend.md) (인증 위임 부분 대체), [ADR-0006](0006-web-structure-and-oidc.md) (프론트 OIDC 흐름 대체)

## Context (맥락)

ADR-0003/0006은 인증을 **사내 기존 IdP(OIDC)에 위임**하고, 백엔드는 JWKS로 토큰을
**검증만**, 프론트는 IdP authorize로 **리다이렉트**하는 구조를 택했다. 전제는 "연동 가능한
사내 IdP(OIDC JWKS·클레임·역할 매핑)가 선결되어 있다"였다(ADR-0003 후속 작업·리스크 참고).

그러나 실제로는 **연동할 IdP가 준비되지 않았고**, 결과적으로:

- 앱 진입 시 `beginLogin()`이 비어 있는 `NEXT_PUBLIC_OIDC_AUTHORITY`로 리다이렉트를 시도해
  "사내 인증으로 이동 중…" 화면에서 멈춘다 — 로그인 자체가 불가능.
- 개발·데모·단독 배포 환경에서 당장 로그인할 수단이 없다.

따라서 **백엔드가 ID/PW를 직접 검증**하고 **자체 JWT를 발급**하는 1차(self-hosted) 인증으로
전환한다. 사내 IdP 연동이 준비되면 OIDC로 복귀할 수 있도록 **기존 OIDC 코드는 보존**한다.

## Decision (결정)

### 1. 백엔드가 ID/PW 검증 + JWT(HS256) 발급

- `POST /api/v1/auth/login` (`username`+`password`) → 자격 검증 후 **HS256 JWT** 발급.
  토큰 subject는 로컬 `users.id`, 클레임에 `preferred_username`·`email`·`roles` 포함(프론트 표시용).
- 비밀번호는 **bcrypt 해시**로 `users.hashed_password`에 보관.
- `get_current_user`는 ① `sk-` API 키, ② 자체 발급 JWT 검증(HS256) 두 경로를 처리.
  기존 JWKS/OIDC 검증(`core/security.verify_token`, `service.provision_user`)은 **보존된 비활성 코드**.
- 워크스페이스 규약대로 HS256 + 공유 시크릿(`JWT_SECRET_KEY`) — 스택 내 서비스 간 동일.

### 2. 계정 생성은 관리자 전용 + seed 관리자

- 공개 회원가입(signup) **없음**. 관리자가 `POST /api/v1/users`로 계정(초기 비밀번호 포함)을 생성.
- 최초 로그인용 **seed SUPERADMIN**을 앱 기동 시 보장(`SEED_ADMIN_*`, 비밀번호 미설정 시 생략).
- 본인 비밀번호 변경: `POST /api/v1/auth/password`.

### 3. 프론트 — 자체 로그인 폼

- `/login`은 IdP 리다이렉트 대신 **ID/PW 폼**. 로그인 성공 시 토큰을 `auth-store`에 저장하고 복귀.
- axios 401 처리는 IdP 재로그인 대신 `/login?redirect=…`로 이동.
- OIDC 흐름 파일(`lib/oidc.ts`·`/auth/callback`·`api/auth.ts`)은 **보존**(현재 경로에서 미사용).

### 4. 스키마 변경

- `llmonl.users`: `hashed_password`(bcrypt) 추가, `idp_subject`는 **nullable**(보존, OIDC 복귀용).
  `init.sql`에 멱등 `ALTER`로 기존 볼륨 마이그레이션 포함.

## Alternatives considered (대안)

| 대안 | 장점 | 기각 사유 |
|------|------|-----------|
| **IdP 연동 완료까지 대기** | ADR-0003 유지 | 연동 IdP 부재로 당장 로그인 불가 — 실용성 없음. |
| **개발용 로컬 우회만 추가** | ADR 유지, 최소 변경 | 두 인증 경로 공존 복잡. 당장 단독 운영 요구에 미흡. |
| **Keycloak 등 IdP 신규 도입** | 표준 OIDC | 운영 부담·범위 초과. 추후 OIDC 복귀 경로로 보류. |

## Consequences (결과)

**긍정**
- IdP 없이도 즉시 로그인·운영 가능. 개발·데모·단독 배포 간소화.
- 인증 계약이 백엔드 내부로 수렴(발급·검증 동일 서비스).

**부정 / 리스크**
- 보안 민감 코드(비밀번호 해싱·토큰 발급)를 앱이 소유 — ADR-0003이 피하려던 지점의 부분 회귀.
  bcrypt·표준 JWT로 리스크를 제한하되, 자작 범위를 로그인·비밀번호 변경으로 최소화.
- `JWT_SECRET_KEY`·`SEED_ADMIN_PASSWORD`를 운영에서 반드시 교체해야 함.
- refresh 토큰 없음 — 만료 시 재로그인.

**후속 작업**
- 사내 IdP 준비 시 OIDC 복귀(보존 코드 재활성) 또는 두 방식 병행 검토.
- 비밀번호 정책·잠금·감사 로깅 등 강화(필요 시).
