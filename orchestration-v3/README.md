# orchestration-v3

LLM 오케스트레이션 플랫폼 v3. **단일 Python 백엔드(FastAPI) + Next.js 프론트엔드** 구성.
설계 결정은 [`docs/adr/`](docs/adr/) 참고 — 특히 [ADR-0003](docs/adr/0003-single-python-backend.md).

## 구조

```
orchestration-v3/
├─ apps/
│  ├─ api/       FastAPI 단일 백엔드 (uv) — LLM + 플랫폼 도메인, OIDC 토큰 검증
│  └─ admin/     Next.js (TS) — 관리자 UI (admin-front 이식, shadcn-admin · OIDC — ADR-0006)
├─ packages/
│  └─ contracts/ api OpenAPI → admin TS 타입 (단방향 생성물)
├─ deploy/       Docker Compose · Nginx · 관측 스택 (V2 계승 예정)
├─ tools/        OpenAPI export 등 유틸
├─ docs/adr/     아키텍처 결정 기록
└─ Taskfile.yml  루트 태스크 러너 (go-task)
```

## 핵심 설계 (ADR-0003)

- **백엔드 단일 언어(Python)** — 폴리글랏의 계약 중복·drift 비용 제거.
- **인증은 사내 기존 IdP(OIDC)에 위임** — FastAPI는 JWKS로 토큰 검증만. SSO/SAML/LDAP는 IdP 담당.
- **moon·교차언어 codegen 불필요** — 얇은 Taskfile + 단방향 OpenAPI→TS 생성.

## 개발

```bash
# 전제: uv, pnpm, go-task 설치
task dev          # api(:8000) + admin(:3000) 동시 기동
task lint
task test
task gen-types    # api OpenAPI → admin TS 타입 재생성
```

개별 서비스:
```bash
cd apps/api && uv sync --group dev && uv run poe dev   # :8000
cd apps/admin && pnpm install && pnpm dev              # :3000
```

## 로컬 디버깅 (브레이크포인트 · 모니터링 서버 제외)

소스 분석을 위해 **api만 디버거로 bare-metal 실행하고, 의존 인프라는 DB(pgvector) 하나만 docker로 띄우는** 구성.
모니터링 스택(grafana·prometheus·loki·promtail·cadvisor)과 Langfuse·Redis·ClickHouse·MinIO는 띄우지 않는다.

- `STORAGE_BACKEND=local` → 첨부는 로컬 디스크(`uploads/`)에 저장, MinIO 불필요
- `LANGFUSE_ENABLED=false` → 관측 콜백·flush가 no-op(`engine/observability/langfuse.py`), Langfuse/Redis/ClickHouse 불필요
- api 런타임의 유일한 필수 의존성은 **pgvector DB**(JWT 검증·장기메모리·전 도메인 영속화)

### 1. DB(pgvector)만 기동

```powershell
cd deploy
docker compose -p orchestration-v3-local --env-file ./environments/local/compose.env up -d db
```

> `-p orchestration-v3-local` 프로젝트명은 반드시 붙인다. 빼면 별도 네트워크에 고립 컨테이너가 떠서 좌표가 어긋난다.

### 2. Langfuse 끄기

`deploy/environments/local/api.env`에서:

```diff
- LANGFUSE_ENABLED=true
+ LANGFUSE_ENABLED=false
```

### 3. api 의존성 동기화 (최초 1회)

```powershell
cd apps/api
uv sync --group dev
```

### 4. VS Code 디버그 실행

1. `orchestration-v3` 폴더를 VS Code로 연다.
2. 분석할 코드에 브레이크포인트를 찍는다.
3. **실행 및 디버그(F5)** → `api: FastAPI debug (no reload)` 선택 (`.vscode/launch.json`).

디버그 구성의 핵심:
- **`--reload` 없음** — uvicorn reload는 하위 프로세스를 띄워 브레이크포인트가 바인딩되지 않는다. 코드 수정 반영이 필요하면 디버그 세션을 재시작한다.
- **`justMyCode: false`** — langgraph·litellm·fastapi 등 라이브러리 내부까지 스텝인 가능(엔진 동작 분석용).
- **`console: integratedTerminal`** — 디버그 세션 중에도 서버 로그가 통합 터미널에 그대로 출력된다.
- `ENV_FILE`로 `api.env`를 주입 → DB는 `localhost:8066`으로 접속.

### 로그 보기 (디버거 없이 터미널 실행)

브레이크포인트 없이 로그만 보며 띄우려면 터미널에서 직접 실행한다.

```powershell
cd apps/api
# poe dev: --reload 포함, 로그가 터미널에 출력됨 (ENV_FILE은 poe가 자동 주입)
uv run poe dev
```

reload 없이 실행하려면 uvicorn을 직접:

```powershell
cd apps/api
$env:ENV_FILE = "../../deploy/environments/local/api.env"
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000
```

- 앱 로그 레벨은 `api.env`의 `LOG_LEVEL`(기본 `INFO`)로 조절한다 — 상세 분석 시 `LOG_LEVEL=DEBUG`.
  `main.py`가 루트 로깅을 설정하므로 도메인·엔진의 `logger.info()`도 터미널에 출력된다.
- 기동 시 DB 연결을 먼저 점검하므로(`core/db.py check_connection`), DB 좌표·비밀번호가 틀리면
  `DB 연결 실패: postgresql://…@host:port/db — <사유>` 로그와 함께 즉시 기동이 중단된다.

### (선택) 프론트엔드

api 분석만이라면 불필요. UI까지 보려면 별도 터미널에서:

```powershell
cd apps/admin;  pnpm install; pnpm dev    # :3000, /api → localhost:8000 프록시
cd apps/portal; pnpm install; pnpm dev
```

### 종료

```powershell
cd deploy
docker compose -p orchestration-v3-local --env-file ./environments/local/compose.env stop db
```
