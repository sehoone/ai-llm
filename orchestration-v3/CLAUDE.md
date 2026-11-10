# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

orchestration-v3 작업 시 가이드. 설계 근거는 `docs/adr/` — 결정 전 반드시 참고. 구조가 표준과 어떻게 정렬되는지·참조 소스는 [`docs/structure-and-references.md`](docs/structure-and-references.md).

> **현재 상태: 이식 진행 중** — 구조·계약·경계는 확정. 구현됨: 플랫폼 도메인(user·api_key·llm_resource)·인증·chat(HITL + 실 LLM + 첨부 + 장기메모리)·rag·artifact·ai_overview(사내 문서 + LLM 키워드 + trgm·pgvector 하이브리드 검색)·meeting(음성 회의록 — 업로드·STT·요약·발행)·관측(Langfuse), 엔진 `llm`·`graph`·`agent`·`rag`·`memory`·`artifact`·`extraction`·`ai_overview`·`transcription`·`observability`·`prompts`. 이식/골격 대기: 도메인 `agent`·`workflow`. 정확한 범위는 아래 "구현 현황" 참고.

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
| [0010](docs/adr/0010-engine-llm-provider.md) | `engine/llm` — ChatLiteLLM 어댑터로 LLM 공급자 추상화. `LlmConfig`만으로 모델 조립(DB 미의존, 도메인이 주입) |
| [0011](docs/adr/0011-chat-streaming-contract.md) | 챗 스트리밍 계약 — SSE + LangGraph `stream_mode="messages"` 토큰 전파, per-request 모델 선택 |
| [0012](docs/adr/0012-engine-rag.md) | `engine/rag` + `domains/rag` — 지식베이스 그룹·문서·검색(chunk·embed, pgvector) |
| [0013](docs/adr/0013-artifacts.md) | 아티팩트 — 스트리밍 산출물 + 버전관리 + 공개 링크(토큰) |
| [0014](docs/adr/0014-attachments-multimodal.md) | 챗 첨부 멀티모달 — 문서 텍스트 추출/이미지 경로 |
| [0015](docs/adr/0015-long-term-memory.md) | 장기 메모리 — mem0 + pgvector(`engine/memory`), opt-in·비차단 |
| [0016](docs/adr/0016-document-text-extraction.md) | 문서 텍스트 추출 — `engine/extraction`(markitdown) |
| [0017](docs/adr/0017-attachment-object-storage-minio.md) | 첨부 객체 저장 — MinIO(S3 호환, `core/storage`), 로컬 디스크 폴백 |
| [0018](docs/adr/0018-env-config-layout.md) | **env 단일 소스** — `deploy/environments/<env>/{compose.env, api.env}`. api.env는 bare-metal 기준(localhost), docker는 compose가 네트워크 좌표 override. app-level `.env*` 제거 |

## 구조

> 최상위는 배포 단위 기준 `apps/*` + `packages/*` 모노레포 레이아웃.

```
apps/api/src/
├─ domains/<d>/   # api·service·repository·schema 계층 (수직 슬라이스 / HTTP 경계)
│                 # chat rag agent workflow meeting user api_key llm_resource auth
├─ engine/        # AI 실행 능력 (ADR-0005) — llm prompts rag agent graph memory artifact extraction observability transcription
├─ core/          # config·security(비밀번호 해싱·JWT 발급/검증; OIDC/JWKS 보존)·db(세션)·response(ApiResponse 래퍼)·storage(MinIO 첨부)
└─ main.py        # 도메인 라우터 등록 지점
apps/web/src/           # shadcn-admin: api·app·features·components·stores·… (ADR-0006, FSD 아님)
packages/contracts/     # api OpenAPI → web TS (생성물, 커밋 안 함 — openapi.json·api-schema.d.ts gitignore)
```

### 구현 현황 (디렉터리 ≠ 구현됨)

- **api 구현·등록 완료**: `domains/user`·`api_key`·`llm_resource`·`chat`·`rag`·`artifact`·`ai_overview`·`meeting`이 `main.py`에 라우터 등록됨(`/api/v1/*`). artifact는 공개 링크용 `public_router`(`/api/v1/public/artifacts`, 미인증)도 등록.
- **인증(api) — 자체 ID/PW (ADR-0009)**: `POST /api/v1/auth/login`이 username+password를 검증하고 **HS256 JWT**를 발급(`core/security.create_access_token`, subject=로컬 user id). 비밀번호는 bcrypt(`users.hashed_password`). `dependencies.py get_current_user`가 두 경로를 처리 — ① `sk-` API 키, ② 자체 JWT(`decode_access_token` 후 user id로 조회). 계정 생성은 관리자 전용(`POST /api/v1/users`) + 기동 시 seed SUPERADMIN(`SEED_ADMIN_*`). 비밀번호 변경 `POST /api/v1/auth/password`. 권한은 `require_admin`·`require_superadmin`. **OIDC(JWKS 검증 `verify_token`·`provision_user`)는 보존된 비활성 코드** — IdP 복귀용.
- **chat(ADR-0008·0010·0011·0014·0015)**: HITL 승인 골격 + 실 LLM. `engine/agent`(정책·레지스트리)·`engine/graph`(interrupt 게이트). 모델 노드는 `_resolve_model` 리졸버(`domains/chat/service.py`)가 per-request `LlmConfig`로 실모델(`engine/llm.build_chat_model` — ChatLiteLLM)을 조립; `FakeToolCallingModel`(`fake_model.py`)은 리졸브 실패 시 기본 폴백. 스트리밍은 SSE + `stream_mode="messages"`(ADR-0011). 첨부(ADR-0014)는 `engine/extraction`(markitdown) 추출 + `core/storage`(MinIO) 저장. 장기 메모리(ADR-0015)는 `engine/memory`(mem0+pgvector, opt-in `MEMORY_ENABLED`). 체크포인터는 InMemory(`checkpointer.py`, `CHAT_CHECKPOINTER=postgres`는 후속).
- **rag(ADR-0012)**: `domains/rag`(그룹·키·문서 CRUD + 검색)가 `engine/rag`(chunk·embed, pgvector) 위임. 수직 슬라이스 구현됨.
- **artifact(ADR-0013)**: `domains/artifact`(스트리밍 산출물·버전관리·공개 링크) + `engine/artifact`(parser). publish 시 토큰 발급, 공개 라우터로 미인증 조회.
- **관측(ADR-0007)**: `engine/observability` 구현(`context`·`langfuse`·`runconfig`). `main.py` lifespan 종료 시 `observability_shutdown()`로 Langfuse 트레이스 flush(비활성이면 no-op). 엔진 경계 준수 — 도메인이 컨텍스트 값을 주입.
- **ai_overview(V2 포팅)**: `domains/ai_overview`(사내 문서 CRUD + JSON 일괄 업로드 + 인메모리 progress job + LLM 키워드/동의어 생성) + `engine/ai_overview`(키워드 추출·답변 스트리밍 프롬프트, 순수). 검색은 **하이브리드** — LLM 질문 키워드 추출 → trgm 키워드 매칭(`pg_trgm`) + pgvector 코사인(`engine/rag` 청킹·임베딩 재사용)을 RRF로 융합 → NDJSON 답변 스트리밍(`POST /search`). 임베딩 리소스 없으면 벡터 축 degrade(trgm 단독). web가 보내는 `model` 문자열은 미사용(v3는 `llm_resource` 기본 chat 리소스) — `llm_resource_id` 재매핑은 후속. 테이블 3종(`ai_overview_document`·`ai_overview_keyword`·`ai_overview_embedding`, `init.sql`).
- **meeting(V2 포팅)**: `domains/meeting`(음성 회의록 — 업로드·전사·요약·화자매핑·발행) + `engine/transcription`(`stt.py` STT, `minutes.py` 요약). 녹음은 전용 MinIO 버킷(`MEETING_AUDIO_BUCKET`)에 격리 저장. `main.py` lifespan 기동 시 `fail_stuck_meetings()`로 중단된 작업 정리. 라우터 `/api/v1/meetings`.
- **api 빈 골격**: `domains/agent`·`workflow`는 `__init__.py`뿐(이식 대기).
- **테스트**: `tests/test_health.py`, `tests/engine/test_approval_policy.py`(HITL 정책), `tests/engine/test_artifact_parser.py`(artifact 파서), `tests/engine/test_ai_overview_keywords.py`(키워드 JSON 파싱), `tests/domains/test_ai_overview_fusion.py`(RRF 융합). deploy 도구는 `tools/tests/test_deploy.py`.
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
task deploy ENV=local        # 전체 스택 빌드+기동 (local|dev|stg|prd — tools/deploy.py)
task deploy-test ENV=local   # 배포 후 로그인 스모크 (tools/smoke_login.py)
task deploy-down ENV=local   # 스택 종료 (prd는 CONFIRM_PRD=prd 필요)

# api (FastAPI, uv)
# env는 deploy/environments/local/api.env 단일 소스(ADR-0018). poe dev가 ENV_FILE로 주입.
# localhost 좌표를 쓰므로 로컬 스택(task deploy ENV=local)이 떠 있어야 DB·관측에 붙는다.
cd apps/api && uv sync --group dev && uv run poe dev     # :8000
uv run poe lint            # ruff check + lint-imports(레이어 경계)
uv run poe format
uv run poe test            # pytest (tests/ — health + HITL 정책)
uv run pytest tests/path/test_x.py::test_y   # 단일 테스트

# web (Next.js, pnpm) — 로컬은 env 불필요. NEXT_PUBLIC_API_URL 비면 `/api` 상대경로
# → next.config rewrite가 localhost:8000으로 프록시. docker는 API_URL build arg 사용.
cd apps/web && pnpm install
pnpm dev                   # :3000
pnpm lint                  # eslint .  (web 테스트 스위트 없음)
pnpm build && pnpm start
```

> ⚠️ uv·ruff·pnpm은 Claude 셸 PATH에 없을 수 있음 — lint/test/build는 사용자가 직접 실행.

### 로컬 docker 스택 운영 (디버깅·반복 시)

`task deploy ENV=local`로 뜬 스택을 **직접 compose로 조작할 때는 반드시 프로젝트명을 맞춘다** — `deploy.py`가 `--project-name orchestration-v3-<env>`를 쓰므로, 빼면 디렉터리명(`deploy`) 기반 **별도 프로젝트/네트워크에 고립 컨테이너**가 떠서 db·langfuse 등 서비스 DNS에 못 붙는다.

```bash
cd deploy
# api만 재빌드·재생성 (전체 task deploy 없이 api 코드 반영)
docker compose -p orchestration-v3-local --env-file ./environments/local/compose.env up -d --build api
```

- **api는 이미지 빌드(소스 bind-mount 없음)**. 배포 스택의 api는 hot-reload가 아니므로 `apps/api/src/**` 수정은 **재빌드해야 반영**된다(`poe dev` bare-metal 모드만 reload). `api.env` 변경도 **컨테이너 재생성** 필요(`env_file`은 기동 시 주입).
- 포트: nginx `:8060`(진입점) · api `:8000` · web `:3000` · postgres `:8066` · langfuse `:8067` · minio 콘솔 `:8068`(S3 API 9000은 호스트 미노출) · grafana `:8064`.
- 컨테이너 내 python은 `/app/.venv/bin/python`(기본 `python`은 앱 의존성 없음). Git Bash에서 `docker exec` 경로가 깨지면 `MSYS_NO_PATHCONV=1` 접두.

## 규칙

- DB 스키마: `llmonl`. pgvector 사용.
- **env 단일 소스(ADR-0018)**: 환경 설정은 `deploy/environments/<env>/{compose.env, api.env}`에만 둔다. app-level `.env*`·`deploy/.env` 추가 금지. 새 api 설정은 `api.env.example`에 추가(bare-metal localhost 기준) + 네트워크 좌표면 `docker-compose.yml` api `environment:` override 추가. 실파일은 커밋 금지.
- 새 도메인은 `apps/api/src/domains/<name>/`에 수직 슬라이스로 추가 후 `main.py`에 라우터 등록.
- **AI 연산은 `engine/`에 위임** (ADR-0005). 도메인은 HTTP 경계+관계형 영속화만. `engine`은 `domains`·FastAPI를 import 금지(단방향 `domains→engine→core`).
- 계약 변경 시 `task gen-types`로 web 타입 재생성(단방향).
- 인증(ADR-0009): 백엔드가 ID/PW 검증·JWT 발급을 소유. `JWT_SECRET_KEY`·`SEED_ADMIN_PASSWORD`는 운영에서 반드시 교체. 자작 범위는 로그인·비밀번호 변경으로 최소화(bcrypt·표준 JWT). OIDC 코드는 보존(비활성) — 복귀 시 재활성.
- **web `src/api/*.ts`는 아직 V2 엔드포인트 기준**(이식 직후). 백엔드 도메인 이식과 함께 `/api/v1/*`·`ApiResponse` 계약으로 재매핑 필요 (ADR-0006 후속).
- **외부 시스템 연동 MCP 서버 추가 시**: `templates/mcp-server/`(복제형 스타터)를 `apps/<name>-mcp/`로 복사해 시작. v3 컨벤션 네이티브(uv·ruff·import-linter, `llmonl` 스키마, 인증은 JWKS 검증만 — ADR-0003). 절차·구조는 `templates/mcp-server/README.md` 참고.

## 팀 협업 (Claude Code)

여러 명이 Claude Code로 함께 개발한다. **공유 설정은 커밋하고 개인 설정은 커밋하지 않는다.**

### 설정 파일 3계층
| 파일 | git | 용도 |
|------|-----|------|
| `.claude/settings.json` | **커밋(공유)** | 팀 공통 권한 allowlist·deny, 공용 hook |
| `.claude/settings.local.json` | gitignore(개인) | 개인 권한·실험. 공유할 가치가 생기면 `settings.json`으로 승격 |
| `~/.claude/settings.json` | 각자 PC(전역) | 개인 모델·테마 등 |

- **공유 명령·에이전트**: `.claude/commands/*.md`(슬래시 명령)·`.claude/agents/*.md`(서브에이전트)는 커밋하면 팀 전원이 공유한다. 현재 `/deploy-test`·`/port-domain`(V2 도메인 이식), `convention-checker` 보유.
- **생성물·비밀파일 가드**: 공유 `settings.json`의 `deny`가 생성물·빌드 산출물·실 비밀파일 편집을 차단한다 — `packages/contracts/**`(gen-types 생성물), `**/*.tsbuildinfo`, `**/api.env`·`**/compose.env`(ADR-0018 실 env). `.example`은 편집 허용.
- **메모리는 공유 금지**: 개인 로컬(`~/.claude/.../memory/`)이다. 팀이 공유할 지식은 메모리가 아니라 **`CLAUDE.md`·`docs/adr/`에 커밋**한다.
- **MCP 서버 공유**: 팀 공용 MCP는 레포 루트 `.mcp.json`에 커밋(비밀값은 env 참조로 분리 — ADR-0018).

### PR·리뷰 루틴
- PR 전 변경분에 `/code-review`(로컬 diff) 또는 `/code-review ultra <PR#>`(클라우드 멀티에이전트). 인라인 코멘트는 `--comment`.
- 레이어/컨벤션 점검은 `convention-checker` 서브에이전트(ADR-0005 경계·수직 슬라이스·ApiResponse·`llmonl`·인증 "검증만").
- 작업은 피처 브랜치에서. `main` 직접 커밋 금지. push·force-push·`reset --hard`는 Claude에게 자동 승인하지 않는다(`settings.json` deny).
- **병렬 작업**: 여러 명/여러 Claude 세션이 동시에 작업하면 git worktree로 격리(브랜치별 디렉터리)해 충돌을 줄인다. Claude Code가 worktree 생성을 지원한다.

### ⚠️ GitHub Actions 위치
GitHub는 **리포 루트(`ai-llm-1/`)의 `.github/workflows`만 실행**한다. 이 리포는 `sehoone/ai-llm` 단일 리포이므로 `orchestration-v3/.github/workflows/ci.yml`은 **현재 실행되지 않는다**(dormant). 동작시키려면 루트로 옮겨야 한다. `@claude` 멘션 워크플로(`ai-llm-1/.github/workflows/claude.yml`)는 루트에 배치됨 — 리포 Secret `ANTHROPIC_API_KEY` 등록 필요.

### (opt-in) 저장 시 자동 ruff format — uv가 PATH에 있는 사람만
프로젝트 관례상 lint/format은 수동(`uv run poe format`)이다. `uv`를 셸 PATH에 올린 팀원은 아래를 **개인** `.claude/settings.local.json`에 넣어 편집 즉시 포맷할 수 있다(공유 `settings.json`에 넣지 말 것 — uv 없는 PC에서 매 편집 에러):
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": "command -v uv >/dev/null 2>&1 && uv run --project apps/api ruff format apps/api/src >/dev/null 2>&1 || true" }
        ]
      }
    ]
  }
}
```
