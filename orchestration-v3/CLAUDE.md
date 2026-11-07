# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

orchestration-v3 작업 시 가이드. 설계 근거는 `docs/adr/` — 결정 전 반드시 참고. 구조가 표준과 어떻게 정렬되는지·참조 소스는 [`docs/structure-and-references.md`](docs/structure-and-references.md).

> **현재 상태: 이식 진행 중** — 구조·계약·경계는 확정. 플랫폼 도메인(user·api_key·llm_resource)·인증·chat(HITL 골격)·관측(Langfuse)은 구현됨. LLM 도메인(rag·agent·workflow·meeting)과 `engine/llm`·`prompts`·`rag`·`memory`·`transcription`은 이식 대기. 정확한 범위는 아래 "구현 현황" 참고.

## 핵심 설계 (ADR-0003)

- **단일 Python 백엔드(FastAPI)** + Next.js 프론트. 폴리글랏(V2)의 계약 중복·drift 제거.
- **인증은 사내 기존 IdP(OIDC)에 위임** — api는 JWKS로 토큰 검증만. 로그인·SSO·SAML·LDAP는 앱이 소유하지 않음. 인증 코드 자작 금지.
- **moon·교차언어 codegen 없음** — 얇은 Taskfile + 단방향 OpenAPI→TS 생성.

## 설계 결정 (ADR) — 변경 전 해당 ADR 확인

| ADR | 결정 |
|-----|------|
| [0003](docs/adr/0003-single-python-backend.md) | 단일 Python 백엔드 + IdP 인증 위임 |
| [0004](docs/adr/0004-apps-packages-monorepo-layout.md) | `apps/*` + `packages/*` 레이아웃 (서비스명 `api`/`web`) |
| [0005](docs/adr/0005-ai-engine-layer.md) | AI 엔진 레이어 분리 (`domains → engine → core`) |
| [0006](docs/adr/0006-web-structure-and-oidc.md) | web은 shadcn-admin 구조 + 프론트 OIDC 리다이렉트 (인증 흐름은 0009 대체) |
| [0007](docs/adr/0007-llm-observability-langfuse.md) | LLM 관측은 Langfuse(self-host)에 위임 — 계측은 `engine/observability`, 컨텍스트는 도메인이 값 주입 |
| [0008](docs/adr/0008-chat-human-approval.md) | 챗 사용자 승인(HITL) — tool call 3-티어 정책(engine) + LangGraph interrupt/재개, 인가·영속은 domain |
| [0009](docs/adr/0009-self-id-password-auth.md) | **자체 ID/PW 인증** — 백엔드가 자격 검증 후 HS256 JWT 발급(0003 IdP 위임 대체). OIDC 코드는 보존(비활성) |

## 구조

> 최상위는 배포 단위 기준 `apps/*` + `packages/*` 모노레포 레이아웃.

```
apps/api/src/
├─ domains/<d>/   # api·service·repository·schema 계층 (수직 슬라이스 / HTTP 경계)
│                 # chat rag agent workflow meeting user api_key llm_resource auth
├─ engine/        # AI 실행 능력 (ADR-0005) — llm prompts rag agent graph memory transcription
├─ core/          # config·security(비밀번호 해싱·JWT 발급/검증; OIDC/JWKS 보존)·db(세션)·response(ApiResponse 래퍼)
└─ main.py        # 도메인 라우터 등록 지점
apps/web/src/           # shadcn-admin: api·app·features·components·stores·… (ADR-0006, FSD 아님)
packages/contracts/     # api OpenAPI → web TS (생성물, 커밋 안 함 — openapi.json·api-schema.d.ts gitignore)
```

### 구현 현황 (디렉터리 ≠ 구현됨)

- **api 구현·등록 완료**: `domains/user`·`api_key`·`llm_resource`·`chat`가 `main.py`에 라우터 등록됨(`/api/v1/*`).
- **인증(api) — 자체 ID/PW (ADR-0009)**: `POST /api/v1/auth/login`이 username+password를 검증하고 **HS256 JWT**를 발급(`core/security.create_access_token`, subject=로컬 user id). 비밀번호는 bcrypt(`users.hashed_password`). `dependencies.py get_current_user`가 두 경로를 처리 — ① `sk-` API 키, ② 자체 JWT(`decode_access_token` 후 user id로 조회). 계정 생성은 관리자 전용(`POST /api/v1/users`) + 기동 시 seed SUPERADMIN(`SEED_ADMIN_*`). 비밀번호 변경 `POST /api/v1/auth/password`. 권한은 `require_admin`·`require_superadmin`. **OIDC(JWKS 검증 `verify_token`·`provision_user`)는 보존된 비활성 코드** — IdP 복귀용.
- **chat(ADR-0008)**: 사용자 승인(HITL) 골격 — `engine/agent`(정책·레지스트리)·`engine/graph`(interrupt 게이트)·`domains/chat`(SSE·영속). 모델 노드는 `FakeToolCallingModel` seam(`engine/graph/fake_model.py`, engine/llm 이식 후 교체), 체크포인터는 InMemory(`checkpointer.py`, postgres는 후속).
- **관측(ADR-0007)**: `engine/observability` 구현(`context`·`langfuse`·`runconfig`). `main.py` lifespan 종료 시 `observability_shutdown()`로 Langfuse 트레이스 flush(비활성이면 no-op). 엔진 경계 준수 — 도메인이 컨텍스트 값을 주입.
- **api 빈 골격**: `domains/rag`·`agent`·`workflow`·`meeting`은 `__init__.py`뿐. `engine/llm`·`prompts`·`rag`·`memory`·`transcription`은 이식 대기(`prompts`·`observability` 외 engine 모듈은 비어 있음).
- **테스트**: `tests/test_health.py`, `tests/engine/test_approval_policy.py`(HITL 정책 단위 테스트) 존재.
- **web**: shadcn-admin 구조 이식 완료. 로그인은 `/login`의 **ID/PW 폼**(`app/login/page.tsx` → `auth/login`), 토큰은 `stores/auth-store.ts`(쿠키). `(authenticated)` 레이아웃이 `access_token` 쿠키 없으면 `/login`. `api/axios.ts`는 Bearer 첨부 + 401 시 `/login` 이동. **OIDC 흐름(`lib/oidc.ts`·`/auth/callback`·`api/auth.ts`)은 보존·미사용**. `src/api/*.ts`는 아직 V2 엔드포인트 기준(아래 규칙 참고).
- 새 도메인 이식 시: 수직 슬라이스(`api`·`service`·`repository`·`schema`) 채우고 `main.py`에 라우터 등록, AI 연산은 `engine/`에 위임.

### 계약·경계 (여러 파일에 걸친 암묵 규칙)

- **응답 래퍼**: 백엔드는 `ApiResponse[T]`(`{success, message, data}`)로 감싼다(`core/response.py`). web `src/api/axios.ts` 인터셉터가 `{success,data}`를 **자동 unwrap**하므로 web 호출부는 `data`만 다룬다.
- **인증 흐름(web)**: ID/PW 자체 로그인(ADR-0009). `(authenticated)` 레이아웃이 `access_token` 쿠키 없으면 `/login` → ID/PW 폼이 `POST /api/v1/auth/login` 호출(전역 401 인터셉터 우회 위해 기본 axios 직접 사용) → 반환 JWT를 `auth-store`에 저장. axios는 Bearer 첨부 + **401이면 refresh 없이 `/login?redirect=…`로 이동**.
- **엔진 격리**: `engine`은 `domains`·FastAPI를 import하지 않는다. `import-linter` 계약(pyproject)이 강제하며 `poe lint`에 포함.

## 명령

```bash
# 루트 (go-task)
task dev            # api(:8000) + web(:3000)
task lint / test
task gen-types      # api OpenAPI → packages/contracts → web TS 재생성 (단방향)

# api (FastAPI, uv)
cd apps/api && uv sync --group dev && uv run poe dev     # :8000
uv run poe lint            # ruff check + lint-imports(레이어 경계)
uv run poe format
uv run poe test            # pytest (tests/ — health + HITL 정책)
uv run pytest tests/path/test_x.py::test_y   # 단일 테스트

# web (Next.js, pnpm)
cd apps/web && pnpm install
cp .env.example .env       # NEXT_PUBLIC_API_URL + NEXT_PUBLIC_OIDC_* 필수
pnpm dev                   # :3000
pnpm lint                  # eslint .  (web 테스트 스위트 없음)
pnpm build && pnpm start
```

> ⚠️ uv·ruff·pnpm은 Claude 셸 PATH에 없을 수 있음 — lint/test/build는 사용자가 직접 실행.

## 규칙

- DB 스키마: `llmonl`. pgvector 사용.
- 새 도메인은 `apps/api/src/domains/<name>/`에 수직 슬라이스로 추가 후 `main.py`에 라우터 등록.
- **AI 연산은 `engine/`에 위임** (ADR-0005). 도메인은 HTTP 경계+관계형 영속화만. `engine`은 `domains`·FastAPI를 import 금지(단방향 `domains→engine→core`).
- 계약 변경 시 `task gen-types`로 web 타입 재생성(단방향).
- 인증(ADR-0009): 백엔드가 ID/PW 검증·JWT 발급을 소유. `JWT_SECRET_KEY`·`SEED_ADMIN_PASSWORD`는 운영에서 반드시 교체. 자작 범위는 로그인·비밀번호 변경으로 최소화(bcrypt·표준 JWT). OIDC 코드는 보존(비활성) — 복귀 시 재활성.
- **web `src/api/*.ts`는 아직 V2 엔드포인트 기준**(이식 직후). 백엔드 도메인 이식과 함께 `/api/v1/*`·`ApiResponse` 계약으로 재매핑 필요 (ADR-0006 후속).
- **외부 시스템 연동 MCP 서버 추가 시**: `templates/mcp-server/`(복제형 스타터)를 `apps/<name>-mcp/`로 복사해 시작. v3 컨벤션 네이티브(uv·ruff·import-linter, `llmonl` 스키마, 인증은 JWKS 검증만 — ADR-0003). 절차·구조는 `templates/mcp-server/README.md` 참고.
