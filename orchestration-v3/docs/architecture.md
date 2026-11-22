# 현행 아키텍처 (Architecture Overview)

> orchestration-v3가 **지금 실제로 어떻게 구성돼 있는지**를 1장으로 요약한다. "왜 이렇게 됐는지(결정·대안·트레이드오프)"는 각 항목의 **근거 ADR** 링크를 따라간다.
>
> - **결정 이력(불변)**: [`adr/`](adr/) — 이 문서는 ADR을 요약하지 않는다. 현행 상태만 담고, 근거는 링크로 위임한다.
> - **구조 근거(외부 표준 정렬)**: [`structure-and-references.md`](structure-and-references.md)
> - 이 문서는 **living doc** — 코드가 바뀌면 갱신한다. ADR과 달리 덮어써도 된다.
> - 최종 갱신: 2026-11-22

---

## 1. 서비스 토폴로지

단일 Python 백엔드 + 프론트 2개(관리자·사용자). 폴리글랏(V2)의 계약 중복·drift를 제거했다. — 근거: [ADR-0003](adr/0003-single-python-backend.md), [ADR-0023](adr/0023-admin-portal-split.md)

```
Browser → Nginx :8060 ─┬─ /        → portal :3000   (Next.js — 사용자 UI)
                       ├─ /admin    → admin  :3000   (Next.js — 관리자 UI, basePath=/admin)
                       └─ /api/v1/* → api    :8000   (FastAPI — 단일 백엔드)
```

- 백엔드·인증·contracts는 두 프론트가 공유한다. — [ADR-0020](adr/0020-user-portal-frontend.md)
- 로컬 docker 스택 포트: nginx `:8060`(진입점)·api `:8000`·admin/portal `:3000`·postgres `:8066`·langfuse `:8067`·minio 콘솔 `:8068`·grafana `:8064`.

## 2. 백엔드 레이어 (`apps/api/src/`)

단방향 의존 `domains → engine → core`. 역방향 import 금지는 `import-linter`가 강제(`poe lint`). — 근거: [ADR-0005](adr/0005-ai-engine-layer.md)

| 레이어 | 책임 | 비고 |
|--------|------|------|
| `domains/<d>/` | HTTP 경계 + 관계형 영속화. 수직 슬라이스(`api`·`service`·`repository`·`schema`·`model`) | AI 연산 직접 수행 금지 |
| `engine/` | AI 실행 능력. FastAPI·domains 비의존 | import-linter로 격리 강제 |
| `core/` | config·db(세션)·security·response(ApiResponse)·storage(MinIO)·ratelimit | 횡단 공통 |

- **응답 래퍼**: 모든 응답은 `ApiResponse[T]`(`{success, message, data}`, `core/response.py`). 프론트 axios 인터셉터가 `data`를 자동 unwrap.
- **수직 슬라이스 네이밍은 단수**(`api`·`model`·`schema`) — 의도된 편차. [structure-and-references.md](structure-and-references.md) §파일 네이밍.

## 3. 도메인 구현 현황 (`main.py` 라우터 등록 기준)

| 도메인 | 라우터 | 상태 | 근거 ADR |
|--------|--------|------|----------|
| `auth` | `/api/v1/auth` | ✅ 구현 — 자체 ID/PW, HS256 JWT 발급 | [0009](adr/0009-self-id-password-auth.md) |
| `user` | `/api/v1/users` | ✅ 구현 — 관리자 전용 계정 생성 + seed SUPERADMIN | [0009](adr/0009-self-id-password-auth.md) |
| `api_key` | `/api/v1/api-keys` | ✅ 구현 | — |
| `llm_resource` | `/api/v1/llm-resources` | ✅ 구현 — per-request 모델 선택 소스 | [0010](adr/0010-engine-llm-provider.md) |
| `chat` | `/api/v1/chat` | ✅ 구현 — HITL + 실 LLM + 첨부 + 장기메모리 + 스트리밍 | [0008](adr/0008-chat-human-approval.md)·[0010](adr/0010-engine-llm-provider.md)·[0011](adr/0011-chat-streaming-contract.md)·[0014](adr/0014-attachments-multimodal.md)·[0015](adr/0015-long-term-memory.md)·[0025](adr/0025-chat-clarification-and-interrupt.md)·[0026](adr/0026-chat-async-streaming.md) |
| `gpts` | `/api/v1/gpts` | ✅ 구현 — 커스텀 GPT(단순 Q/A, HITL 미사용) | — |
| `project` | `/api/v1/projects` | ✅ 구현 — 대화·지침·지식 작업공간 | [0021](adr/0021-projects.md) |
| `skill` | `/api/v1/skills` | ✅ 구현 — 재사용 지침 프리셋 | [0024](adr/0024-skills-instruction-presets.md) |
| `connector` | `/api/v1/connectors` | ✅ 구현 — 사내 MCP 서버 도구 확장 | [0022](adr/0022-connectors-mcp.md) |
| `rag` | `/api/v1/rag` | ✅ 구현 — 지식베이스 그룹·문서·검색 | [0012](adr/0012-engine-rag.md) |
| `artifact` | `/api/v1/artifacts` (+ `/public/artifacts` 미인증) | ✅ 구현 — 스트리밍 산출물·버전관리·공개 링크 | [0013](adr/0013-artifacts.md) |
| `meeting` | `/api/v1/meetings` | ✅ 구현 — 음성 회의록(업로드·STT·요약·발행) | — |
| `workflow` | `/api/v1/workflows` (+ trigger) | ✅ 구현 — 노드 그래프 실행 + 스케줄러 | [0019](adr/0019-workflow-engine.md) |
| `agent` | — | ⬜ 골격만(`__init__.py`) — 이식 대기 | — |

> **ADR 상태**: 구현 완료된 `workflow`([ADR-0019](adr/0019-workflow-engine.md))·`portal`([ADR-0020](adr/0020-user-portal-frontend.md))은 `Accepted`로 승격됨(2026-11-22). 아직 미구현이라 `Proposed`로 남은 것: 체크포인터 운영([ADR-0029](adr/0029-chat-checkpointer-operations.md))·async DB([ADR-0027](adr/0027-async-db-session.md))·plugin([ADR-0030](adr/0030-plugins.md)).

## 4. AI 엔진 (`engine/`)

도메인이 값을 주입하고 엔진이 실행한다. 엔진은 DB·HTTP를 모른다.

| 엔진 | 책임 | 근거 ADR |
|------|------|----------|
| `llm` | ChatLiteLLM 어댑터 — `LlmConfig`로 모델 조립, 토큰 스트리밍 | [0010](adr/0010-engine-llm-provider.md) |
| `prompts` | 프롬프트 합성 | — |
| `graph` | LangGraph — interrupt 승인 게이트·재개 | [0008](adr/0008-chat-human-approval.md)·[0025](adr/0025-chat-clarification-and-interrupt.md) |
| `agent` | 도구 정책(3-티어)·레지스트리 | [0008](adr/0008-chat-human-approval.md) |
| `rag` | chunk·embed·검색(pgvector) | [0012](adr/0012-engine-rag.md) |
| `memory` | 장기 메모리(mem0 + pgvector, opt-in) | [0015](adr/0015-long-term-memory.md) |
| `artifact` | 스트림 파서 | [0013](adr/0013-artifacts.md) |
| `extraction` | 문서 본문 추출(markitdown) | [0016](adr/0016-document-text-extraction.md) |
| `transcription` | STT·회의록 요약 | — |
| `observability` | Langfuse 계측(context·runconfig) | [0007](adr/0007-llm-observability-langfuse.md) |
| `workflow` | 노드 그래프 실행 엔진 | [0019](adr/0019-workflow-engine.md) |

## 5. 횡단 관심사

- **인증** ([ADR-0009](adr/0009-self-id-password-auth.md)): 백엔드가 ID/PW 검증 + HS256 JWT 발급을 소유. 비밀번호는 bcrypt. `get_current_user`가 ① `sk-` API 키 ② 자체 JWT 두 경로 처리. **OIDC/JWKS 코드는 보존·비활성**(IdP 복귀용) — [ADR-0003](adr/0003-single-python-backend.md)·[ADR-0006](adr/0006-web-structure-and-oidc.md).
- **관측** ([ADR-0007](adr/0007-llm-observability-langfuse.md)): Langfuse(self-host)에 위임. 계측은 `engine/observability`, 컨텍스트 값은 도메인이 주입. lifespan 종료 시 flush.
- **저장** ([ADR-0017](adr/0017-attachment-object-storage-minio.md)): 첨부는 MinIO(S3 호환, `core/storage`), 로컬 디스크 폴백. 회의 녹음은 전용 버킷 격리.
- **env 단일 소스** ([ADR-0018](adr/0018-env-config-layout.md)): `deploy/environments/<env>/{compose.env, api.env}`에만. app-level `.env*` 금지. api.env는 bare-metal(localhost) 기준, docker는 compose가 네트워크 좌표 override.
- **DB**: PostgreSQL `llmonl` 스키마 + pgvector. `ddl-auto` 없이 `init.sql`로 테이블 선관리. 체크포인터는 InMemory 기본, Postgres는 후속([ADR-0028](adr/0028-langgraph-postgres-checkpointer.md)·[0029](adr/0029-chat-checkpointer-operations.md)).

## 6. 프론트 (`apps/admin`·`apps/portal`)

- `admin`: shadcn-admin 구조(FSD 아님), basePath=/admin. — [ADR-0006](adr/0006-web-structure-and-oidc.md)·[ADR-0023](adr/0023-admin-portal-split.md)
- `portal`: 린 구성(shadcn 미복제), nginx 루트 `/`. — [ADR-0020](adr/0020-user-portal-frontend.md)
- 로그인은 `/login` ID/PW 폼 → `auth/login` → JWT를 쿠키/`auth-store`에 저장. axios가 Bearer 첨부 + 401 시 `/login` 이동.
- 타입은 `packages/contracts`가 api OpenAPI → TS 단방향 생성(`task gen-types`, 커밋 안 함).
- ⚠️ admin `src/api/*.ts` 일부는 아직 V2 엔드포인트 기준 — `/api/v1/*`·`ApiResponse` 계약으로 재매핑 진행 중.

## 7. 미구현 / 대기

- `domains/agent` — 골격만. 이식 대기(`/port-domain agent`).
- chat Postgres 체크포인터 — 현재 InMemory. [ADR-0028](adr/0028-langgraph-postgres-checkpointer.md)·[0029](adr/0029-chat-checkpointer-operations.md).
- async DB 세션 — 단계적·조건부. [ADR-0027](adr/0027-async-db-session.md).
- plugin 도메인 — 설계 단계. [ADR-0030](adr/0030-plugins.md).
- gpts 전용 `rag_key` 지식베이스 검색 미연결.

---

### 관련 문서
- [`adr/README.md`](adr/README.md) — ADR 전체 목록·상태
- [`structure-and-references.md`](structure-and-references.md) — 구조가 외부 표준과 어떻게 정렬되는지
- [`v2-chat-migration-roadmap.md`](v2-chat-migration-roadmap.md) — V2 chat 이식 로드맵
- [`portal-roadmap.md`](portal-roadmap.md) — 사용자 포털 로드맵
