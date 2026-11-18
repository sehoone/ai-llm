# ADR-0020: 사용자 포털 프론트 분리 (apps/portal)

- 상태: Proposed
- 날짜: 2026-11-15
- 결정자: sehoone
- 관련: [ADR-0023](0023-admin-portal-split.md) (**상위 결정** — 관리자/사용자 포털 분리; 본 ADR은 그 프론트 구현) · [ADR-0004](0004-apps-packages-monorepo-layout.md) (apps/* 레이아웃 — 세 번째 앱 추가) · [ADR-0006](0006-web-structure-and-oidc.md) (web = 관리자 UI) · [ADR-0009](0009-self-id-password-auth.md) (자체 ID/PW 인증 — 셀프 가입 추가로 확장) · [ADR-0003](0003-single-python-backend.md) (단일 백엔드 유지)

## Context (맥락)

현재 프론트는 `apps/web` 하나다. shadcn-admin 기반 **관리자 UI**(ADR-0006)인데, features에
관리성 기능(`users`·`api-keys`·`llm-resources`·`settings`)과 **최종 사용자 기능**(`chats`·`gpts`·
`ai-overview`·`meeting-minutes`·`natural-search`)이 한 앱에 섞여 있다.

이제 **일반 사용자가 쓰는 화면을 별도로** 구성하려 한다. 사용자 화면은 관리자와 요구가 다르다:

- **UX·브랜딩**: 관리자용 밀도 높은 테이블·차트가 아니라, 챗·검색 중심의 단순·제품형 UI.
- **번들·성능**: 관리자용 무거운 테이블/폼 코드가 사용자 번들에 섞이면 안 된다.
- **노출면(보안)**: 관리자 코드·라우트가 사용자에게 내려가지 않아야 한다.

백엔드(`apps/api`)는 단일 Python 백엔드(ADR-0003)이고, 역할 가드(`require_admin`/
`require_superadmin`)와 자체 JWT 인증(ADR-0009), 단방향 타입 생성물(`packages/contracts`)을
이미 갖췄다. 즉 **바꿀 것은 프론트 경계이지 백엔드 아키텍처가 아니다.**

## Decision (결정)

### 1. 사용자 전용 Next.js 앱 `apps/portal` 신설 — 백엔드는 공유

프론트만 역할별로 둘로 나눈다. 백엔드·DB·인증·`packages/contracts`는 **그대로 공유**한다.

```
apps/
├─ api/        FastAPI 단일 백엔드 (변경 최소 — §3 인증/스코핑만 보강)
├─ web/        관리자 UI (기존, ADR-0006) — basePath=/admin 추가
└─ portal/     사용자 UI (신규) — shadcn 베이스만 재사용, 제품형 UX
packages/
├─ contracts/  (기존) OpenAPI→TS 타입 — portal도 동일 소비
└─ ui/         (후속·선택) 공용 shadcn 프리미티브·axios 래퍼·auth-store 패턴
```

- 배포 가능한 것은 전부 `apps/*`(ADR-0004) — `portal`은 세 번째 배포 단위.
- compose 서비스명·내부 DNS도 `portal`로 통일(ADR-0004 §2 관례 계승).
- **공유 코드는 "복사로 시작 → 중복이 커지면 `packages/ui`로 추출"**. 조기 추상화 지양(YAGNI).
  타입은 이미 `packages/contracts`로 공유되므로 즉시 재사용.

### 2. 라우팅 — 단일 도메인 경로 분리 (`/` = portal, `/admin` = web)

nginx 단일 진입점(`:8060`)을 유지하고 location만 추가한다.

| 경로 | 업스트림 | 비고 |
|------|----------|------|
| `/`       | `portal:3000` | 사용자(기본 랜딩) |
| `/admin`  | `web:3000`    | 관리자 — Next.js `basePath: '/admin'` |
| `/api/*`  | `api:8000`    | 공유 백엔드 (변경 없음) |
| `/health` | `api:8000`    | 기존 유지 |

- `apps/web`은 `next.config`에 `basePath: '/admin'` 추가 → 정적 자산·라우트가 `/admin` 하위로 격리.
- compose에 `portal` 서비스 1개 + nginx `location /admin/`·`location /` 블록 추가로 끝난다.
- **운영 서브도메인(`app.`/`admin.`)은 후속 선택지로 열어 둔다** — 쿠키/CORS 경계가 더 깨끗하고
  관리자 노출면이 작다. 경로 분리에서 서브도메인으로의 전환은 nginx server_name 교체로 가능하도록
  프론트 쪽 절대경로 가정을 피한다(상대경로·`basePath` 기준 유지).

### 3. 인증·권한 — 공유 JWT + 셀프 가입 추가 (ADR-0009 확장)

로그인 엔드포인트(`POST /api/v1/auth/login`)·HS256 JWT·쿠키 저장 패턴은 **두 앱이 공유**한다.
포털도 같은 토큰 체계를 쓰고 로그인 후 랜딩만 다르다. 다음을 보강한다:

1. **역할 모델**: 기본 `USER` 역할을 명시한다. 관리자 엔드포인트는 이미 `require_admin`로
   가드되므로 **USER 토큰은 관리자 API에서 자동 차단** — 백엔드 가드 신규 작성은 불필요.
2. **셀프 가입 신설**: `POST /api/v1/auth/register` 추가 — username/email 중복검증 + bcrypt 해싱
   후 `role=USER`로 생성, 발급 JWT 반환. ADR-0009의 "계정 생성은 관리자 전용"을 **일반 사용자
   한정으로 완화**(관리자/슈퍼관리자 승격은 여전히 관리자 전용). 가입 정책(이메일 인증·도메인
   화이트리스트·초대코드 등)은 구현 시 세부 결정.
3. **데이터 스코핑(가장 중요)**: 포털에서 노출되는 도메인(`chat`·`gpts`·`artifact`·`meeting`·
   `rag`·`ai_overview`)이 **본인 데이터만** 반환하도록 `user_id` 소유권 필터를 점검·강제한다.
   관리자 UI는 전체를 보지만 포털은 요청자 소유만 봐야 한다 — **보안상 핵심 선결 과제**.
   누락 시 IDOR(타 사용자 데이터 열람) 위험.

### 4. 적용 범위 (경로·설정 추가)

`deploy/docker-compose.yml`(portal 서비스) · `deploy/nginx/nginx.conf`(location 2블록) ·
`apps/web/next.config.mjs`(basePath) · `apps/portal/*`(신규 앱) · `Taskfile.yml`(dev/build에 portal) ·
`deploy/environments/*/compose.env`(portal 포트) · 각 `README.md`·`CLAUDE.md`.

## Alternatives considered (대안)

| 대안 | 장점 | 기각 사유 |
|------|------|-----------|
| **별도 앱 `apps/portal`** (채택) | 번들·테마·배포·노출면 완전 분리, ADR-0004 정렬 | 앱 2개 운영, 공유코드 패키지화 필요(수용 가능) |
| 기존 web에 route-group `(user)`/`(admin)` | 코드 공유 쉬움, 앱 1개 | 번들 분리 안 됨 — 관리자 코드가 사용자에 내려감, 레이아웃/테마 충돌, 노출면 리스크 |
| 백엔드도 분리(사용자용 BFF 신설) | 노출면 최소 | 단일 백엔드(ADR-0003) 핵심 결정 역행 — 계약 중복·drift 재발. 과잉. |
| 서브도메인 즉시 도입 | 경계 가장 깨끗 | 인증서·DNS·CORS 선작업 필요. 경로 분리로 시작해 후속 전환이 비용 효율적. |

## Consequences (결과)

**긍정**
- 사용자/관리자의 **UX·번들·노출면이 앱 경계로 분리**된다.
- 백엔드·인증·타입은 공유 유지 — ADR-0003(단일 백엔드)·drift 제거 원칙 보존.
- nginx 단일 진입점·compose 패턴을 그대로 쓰므로 배포 변경이 작다.
- 경로 분리로 시작하되 서브도메인 전환 여지를 남겨 운영 성숙에 맞춰 이동 가능.

**부정 / 리스크**
- **데이터 스코핑이 선결 과제** — 도메인별 `user_id` 소유권 필터 감사 전에는 포털 노출 금지.
- 앱 2개 운영(빌드·배포·의존성)·공유코드 중복 관리 부담. 중복이 커지면 `packages/ui` 추출 필요.
- `apps/web`에 `basePath` 도입 시 기존 절대경로 가정·링크 점검 필요.
- 셀프 가입은 스팸/남용 표면을 연다 — 가입 정책(이메일 인증·레이트리밋) 동반 필요.

**진행 현황**
- ✅ **데이터 스코핑 감사·수정** — 6개 포털 노출 도메인 전수 점검 완료. chat·gpts·artifact·meeting은
  소유권 스코핑 적정. **수정**: `rag` 문서 `list_documents`/`delete_document`에 소유권 필터 추가(본인 문서만,
  공유는 admin), `ai_overview` 관리 엔드포인트 전부 `require_admin`화(`/search`만 사용자 허용).
- ✅ **`apps/portal` 최소 골격** — 로그인(`/login`)·인증 게이트(`(authenticated)`)·랜딩·axios(ApiResponse
  unwrap·401 재로그인)·auth-store(쿠키 JWT). shadcn 전체 미복제(린 구성).
- ✅ **배선** — `apps/web` basePath=`/admin`(+ API rewrite `basePath:false`), nginx `/`→portal·`/admin`→web,
  compose `portal` 서비스, Taskfile `dev-portal`/`lint-portal`.
- ✅ **셀프 가입** — `POST /api/v1/auth/register`(role 서버 고정=USER·bcrypt·username/email 중복검증 409,
  가입 즉시 JWT 발급) + portal `/register` 페이지(로그인 ↔ 가입 상호 링크). 권한 상승 방지: role은 요청에서 안 받음.
- ✅ **가입 남용 방지(1차)** — 경량 인메모리 IP 레이트리밋(`core/ratelimit.py`): register 5회/5분, login 20회/분(429).
  **단일 프로세스 한정** — 수평 확장 시 공유 저장소(Redis) 필요. 이메일 인증·초대코드는 미구현(후속).
- ✅ **공개 공유 링크(basePath 대응)** — artifact·meeting의 공유 URL을 `origin/admin/artifact/{token}`으로 수정
  (web이 `/admin` 하위). `Link`·`router`·`redirect()`·web axios 401은 이미 basePath 반영.
- ✅ **chat 이식(1차)** — portal `(authenticated)/chat`: 세션 목록·생성, 메시지 조회, **fetch 기반 SSE 토큰
  스트리밍**(`lib/sse.ts`·`api/chat.ts`), 제목 자동갱신. **HITL 승인·첨부·아티팩트는 미지원**(승인 필요 시 안내 후 중단).

**후속 작업 / 미결**
- **"클로드급" 챗 고도화 로드맵** — 단계별 계획은 [`../portal-roadmap.md`](../portal-roadmap.md).
  Phase 1(코어 챗: 디자인시스템·마크다운·스트리밍 제어·재생성·대화관리·테마) → Phase 2(첨부·아티팩트) →
  Phase 3(HITL·GPTs·RAG·메모리) → Phase 4(제품화 마감).
- **가입 남용 방지(2차)** — 이메일 인증·초대코드·공유 저장소 기반 레이트리밋.
- **공개 뷰 relocation(선택)** — `/admin/artifact`가 공개 링크에 들어가는 게 어색하면 공개 뷰어를 portal 루트로 이전.
- portal 첫 빌드 전 `cd apps/portal && pnpm install`로 lockfile 생성(앱별 lockfile 구조).
- 중복 누적 시 `packages/ui` 추출.
- (선택) 운영 서브도메인(`app.`/`admin.`) 전환 ADR.
