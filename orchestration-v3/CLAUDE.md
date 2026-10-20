# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

orchestration-v3 작업 시 가이드. 설계 근거는 `docs/adr/` — 결정 전 반드시 참고. 구조가 표준과 어떻게 정렬되는지·참조 소스는 [`docs/structure-and-references.md`](docs/structure-and-references.md).

> **현재 상태: 골격(skeleton)** — V2에서 도메인 로직 이식 중. 아래 "구현 현황" 참고. 구조·계약·경계는 확정, 내용물은 이식 대기.

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
| [0006](docs/adr/0006-web-structure-and-oidc.md) | web은 shadcn-admin 구조 + 프론트 OIDC 리다이렉트 |

## 구조

> 최상위는 배포 단위 기준 `apps/*` + `packages/*` 모노레포 레이아웃.

```
apps/api/src/
├─ domains/<d>/   # api·service·repository·schema 계층 (수직 슬라이스 / HTTP 경계)
│                 # chat rag agent workflow meeting user api_key llm_resource auth
├─ engine/        # AI 실행 능력 (ADR-0005) — llm prompts rag agent graph memory transcription
├─ core/          # config·security(OIDC)·DI·미들웨어
└─ main.py        # 도메인 라우터 등록 지점
apps/web/src/           # shadcn-admin: api·app·features·components·stores·… (ADR-0006, FSD 아님)
packages/contracts/     # api OpenAPI → web TS (생성물, 커밋 안 함 — openapi.json·api-schema.d.ts gitignore)
```

### 구현 현황 (디렉터리 ≠ 구현됨)

- **api 구현·등록 완료**: `domains/user`·`api_key`·`llm_resource`만 `main.py`에 라우터 등록됨(`/api/v1/*`).
- **api 빈 골격**: `domains/chat`·`rag`·`agent`·`workflow`·`meeting`·`auth`는 `__init__.py`뿐. `engine/*`도 사실상 빈 상태(이식 대기). `chat` 라우터 등록은 `main.py`에 주석으로 예약됨.
- **web**: shadcn-admin 구조·auth 흐름(`lib/oidc.ts`·`stores/auth-store.ts`·`(authenticated)` 레이아웃·`api/axios.ts`) 이식 완료. `src/api/*.ts`는 아직 V2 엔드포인트 기준(아래 규칙 참고).
- 새 도메인 이식 시: 수직 슬라이스(`api`·`service`·`repository`·`schema`) 채우고 `main.py`에 라우터 등록, AI 연산은 `engine/`에 위임.

### 계약·경계 (여러 파일에 걸친 암묵 규칙)

- **응답 래퍼**: 백엔드는 `ApiResponse[T]`(`{success, message, data}`)로 감싼다(`core/response.py`). web `src/api/axios.ts` 인터셉터가 `{success,data}`를 **자동 unwrap**하므로 web 호출부는 `data`만 다룬다.
- **인증 흐름(web)**: 자체 로그인 없음. `(authenticated)` 레이아웃이 `access_token` 쿠키 없으면 `/login`→`lib/oidc.ts beginLogin()`(IdP authorize, PKCE)→`/auth/callback` code 교환→`auth-store` 저장. axios는 Bearer 첨부 + **401이면 refresh 없이 IdP 재로그인**.
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
uv run poe test            # pytest (현재 테스트 없음)
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
- 인증 관련 변경은 "검증만" 원칙 준수 — 토큰 발급·세션은 IdP 소유.
- **web `src/api/*.ts`는 아직 V2 엔드포인트 기준**(이식 직후). 백엔드 도메인 이식과 함께 `/api/v1/*`·`ApiResponse` 계약으로 재매핑 필요 (ADR-0006 후속).
- **외부 시스템 연동 MCP 서버 추가 시**: `templates/mcp-server/`(복제형 스타터)를 `apps/<name>-mcp/`로 복사해 시작. v3 컨벤션 네이티브(uv·ruff·import-linter, `llmonl` 스키마, 인증은 JWKS 검증만 — ADR-0003). 절차·구조는 `templates/mcp-server/README.md` 참고.
