# ADR-0004: apps/* + packages/* 모노레포 레이아웃 채택

- 상태: Accepted
- 날짜: 2026-10-17
- 결정자: sehoon
- 관련: [ADR-0003](0003-single-python-backend.md) (디렉토리 구조 섹션 5 개정 — 그 외 결정은 유효)

## Context (맥락)

ADR-0003은 2서비스(단일 Python 백엔드 + TS 프론트) 구조를 확정하며 최상위 디렉토리를
`backend/` · `frontend/` · `contracts/`로 두었다. 골격 스캐폴딩 후 이 네이밍을 재검토하며 두 문제를 확인했다:

- **`backend`/`frontend`는 역할(layer) 이름**이다. 서비스가 늘거나(예: 백그라운드 워커) 성격이
  갈릴 때("프론트"가 아닌 CLI·SDK 등) 최상위 이름이 실제 배포 단위와 어긋난다.
- 유명 AI/풀스택 오픈소스는 **배포 단위(deployable) 이름**을 쓴다. 조사 결과:
  - **Dify** — 백엔드 `api/`, 프론트 `web/` (역할이 아닌 산출물 이름).
  - **n8n** — `packages/*`(cli·core·workflow·frontend·nodes-base) pnpm 모노레포.
  - **Turborepo/Nx 관례** — 배포 가능한 것은 `apps/*`, 공유물은 `packages/*`.

ADR-0003의 핵심 결정(단일 Python 백엔드, IdP 인증 위임, drift 제거, moon→Taskfile)은
그대로 유효하다. 바뀌는 것은 **최상위 디렉토리 네이밍·배치**뿐이다.

## Decision (결정)

### 1. 최상위를 `apps/*` + `packages/*`로 재배치

| 이전 (ADR-0003) | 이후 (본 ADR) | 성격 |
|-----------------|---------------|------|
| `backend/`   | `apps/api/`           | 배포 단위 (FastAPI) |
| `frontend/`  | `apps/web/`           | 배포 단위 (Next.js) |
| `contracts/` | `packages/contracts/` | 공유 생성물 (OpenAPI→TS) |

```
orchestration-v3/
├─ apps/
│  ├─ api/        # FastAPI (uv) — domains/{chat,rag,agent,workflow,meeting,
│  │             #   user,api_key,llm_resource,auth} + core/
│  └─ web/        # Next.js (FSD: app/features/entities/shared)
├─ packages/
│  └─ contracts/  # api OpenAPI → web TS 타입 (단방향 생성물, 커밋 안 함)
├─ deploy/  tools/  docs/adr/  Taskfile.yml
```

- 배포 가능한 것은 전부 `apps/*`. 향후 **백그라운드 워커(`apps/worker/`)** 가 분리되면 같은 층에 추가.
- 서비스 간 공유물은 `packages/*`. 현재는 `contracts`뿐이며 필요 시 확장.

### 2. 컴포즈 서비스명·내부 DNS도 `api`/`web`으로 통일

디렉토리와 런타임 식별자를 일치시킨다 — compose 서비스명 `backend→api`·`frontend→web`,
이를 참조하는 `nginx.conf` upstream과 `prometheus.yml` scrape target도 함께 정렬.

### 3. 적용 범위 (경로 참조 일괄 갱신)

`Taskfile.yml` · `tools/export_openapi.py` · `apps/web/package.json`(gen:types) ·
`apps/api/pyproject.toml` · `deploy/docker-compose.yml` · `deploy/nginx/nginx.conf` ·
`deploy/prometheus/prometheus.yml` · `.github/workflows/ci.yml`(paths-filter·working-directory) ·
`.gitignore` · 각 `README.md`·`CLAUDE.md`.

> Python `src.` import는 각 앱 루트 기준이라 **애플리케이션 코드 import는 영향 없음**.

## Alternatives considered (대안)

| 대안 | 장점 | 기각 사유 |
|------|------|-----------|
| **`backend/` · `frontend/` 유지** (ADR-0003) | 변경 없음 | 역할 이름이라 배포 단위 확장 시 어긋남. |
| **`api/` · `web/` 최상위 평면** (Dify식) | 가장 단순, 변경 최소 | 워커 등 배포 단위 추가 시 `apps/` 그룹핑 부재로 공유물과 섞임. |
| **`server/` · `client/`** | 직관적 | `client`가 모바일/CLra과 혼동. 역할 이름 한계는 동일. |
| **`apps/*` + `packages/*`** (채택) | 배포 단위·공유물 분리, Turborepo/Nx 표준, 확장 명확 | 중첩 한 단계 증가(수용 가능). |

## Consequences (결과)

**긍정**
- 최상위가 **배포 단위를 그대로 반영** — 워커·추가 서비스 확장 시 자리(`apps/*`)가 분명.
- 공유물(`packages/*`)과 배포물(`apps/*`)의 경계가 디렉토리로 강제됨.
- Dify·n8n·Turborepo 등 **업계 통용 레이아웃**과 정렬.

**부정 / 리스크**
- 경로 참조가 여러 설정에 흩어져 있어 **일괄 갱신 필요**(본 ADR에서 완료).
- 중첩이 한 단계 깊어져 상대 경로(`packages/contracts`)가 길어짐.

**후속 작업 / 미결 (별도 ADR 후보)**
- **AI 엔진 레이어 분리 검토** — Dify `core/`(agent·rag·workflow·model_runtime·prompt·tools),
  n8n `workflow`+`core` 조사에서 공통적으로 "AI 실행 엔진을 HTTP 도메인에서 분리"하는 패턴을 확인했다.
  현재 `apps/api/src/domains/{chat,rag,agent,workflow}`에 평탄화돼 있으나, 로직이 커지면
  `domains`(HTTP 경계)와 `engine`(prompts·graph·tools·model_runtime·ingestion)으로 분리하는 안을
  **별도 ADR로 다룬다**. 사내 bounded 플랫폼 규모상 plugin/멀티벡터스토어 추상화 등 과도한 확장은 지양(YAGNI).
