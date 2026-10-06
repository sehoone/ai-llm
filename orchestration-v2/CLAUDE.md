# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Workspace Structure

관심사 분리(Separation of Concerns) 원칙으로 구성된 LLM 오케스트레이션 플랫폼 monorepo.

| Directory | Stack | Description |
|-----------|-------|-------------|
| `orchestrator-server/` | Python 3.13+, FastAPI, LangGraph | LLM 채팅·RAG·워크플로우 엔진 |
| `platform-server/` | Java 21, Spring Boot 3.4 | 인증·사용자·LLM 리소스 관리 |
| `admin-front/` | Next.js 16, TypeScript, pnpm | 관리자 프론트엔드 |
| `deploy/` | Docker Compose, Nginx | 프로덕션 배포 |

모듈 상세: `orchestrator-server/CLAUDE.md`, `admin-front/CLAUDE.md`, `platform-server/CLAUDE.md`

---

## System Architecture

```
Browser / API client
        │
        ▼
  :8060  Nginx (단일 진입점)
        │
        ├── /api/v1/auth/*          → platform-server:8080  (Spring Boot)
        ├── /api/v1/users/*         → platform-server:8080
        ├── /api/v1/api-keys/*      → platform-server:8080
        ├── /api/v1/llm-resources/* → platform-server:8080
        │
        ├── /api/*                  → orchestrator-server:8000 (FastAPI)
        │     ├── /chatbot          LLM 채팅 (SSE 스트리밍)
        │     ├── /agents           AI 에이전트
        │     ├── /rag              RAG 파이프라인
        │     ├── /workflows        DAG 워크플로우
        │     ├── /voice-evaluation 음성 평가
        │     └── /meetings         음성 회의록 (업로드→전사→AI 요약)
        │
        └── /*                      → admin-front:3000 (Next.js)

JWT 흐름 (HS256 전용)
  Client → POST /api/v1/auth/login → platform-server 발급 (HS256)
                                   → orchestrator-server 동일 JWT_SECRET_KEY로 검증

JWT payload (서비스 간 공유 계약):
  { "sub": "<user_id>", "username": "...", "email": "...", "role": "USER|ADMIN|SUPERADMIN|MANAGER|CASHIER",
    "iat": 0, "exp": 0, "jti": "<uuid>" }
  orchestrator-server는 sub(user_id)를 사용. 역할 값은 대문자.

PostgreSQL + pgvector  (schema: llmonl)
  ├── 테이블 생성: deploy/postgres/init.sql (Docker 볼륨 최초 1회) — platform·orchestrator
  │   양쪽 테이블을 모두 생성. ⚠️ orchestrator-server는 startup에 SQLModel create_all이 없음
  │   (자동 생성 아님) → 새 테이블은 init.sql(+ 참조본 orchestrator-server/schema.sql)에 DDL을
  │   추가하고, 이미 떠 있는 DB에는 docker exec psql로 수동 적용해야 함.
  ├── platform-server 소유: users, api_key, refresh_token, llm_resource
  │   └── JPA ddl-auto: none(local) | validate(dev/staging/prod) | create-drop(test)
  │       → 기동 전 llmonl 스키마·테이블이 DB에 존재해야 함
  └── orchestrator-server 소유: session, gpt_chat_message, rag_embedding, workflow,
                               meeting / meeting_segment / meeting_minutes, ...

Observability
  ├── Prometheus  :8063  ← FastAPI /metrics + cAdvisor
  ├── Grafana     :8064  ← Prometheus (대시보드 자동 프로비저닝)
  └── cAdvisor    :8065  ← 컨테이너 리소스 메트릭

Langfuse v3 (LLM 트레이싱)
  ├── ClickHouse  ← 트레이스 데이터
  ├── Redis       ← 작업 큐
  └── MinIO       ← 이벤트·미디어 blob
```

---

## Quick Start (Development)

Each service has a detailed `CLAUDE.md` — read it before editing that service.

### platform-server (`platform-server/`)
```powershell
cd platform-server
cp .env.example .env.local   # JWT_SECRET_KEY, POSTGRES_* 설정
$env:APP_ENV='local'; ./gradlew bootRun

./gradlew test                                           # H2 인메모리
./gradlew test --tests "com.sehoon.platform.auth.AuthServiceTest"
./gradlew compileJava                                    # 컴파일만
./gradlew bootJar                                        # 실행 가능 JAR
```
Swagger UI: `http://localhost:8080/swagger-ui/index.html`

> **중요**: `JWT_SECRET_KEY`는 orchestrator-server와 반드시 동일한 값이어야 합니다.
> `local` 프로필은 `ddl-auto: none` — DB에 `llmonl` 스키마와 테이블이 미리 존재해야 합니다.

### orchestrator-server (`orchestrator-server/`)
```powershell
cd orchestrator-server
uv sync --group dev                # Install deps including poethepoet
cp .env.example .env.development   # fill in secrets
$env:APP_ENV='development'; uv run poe dev   # hot-reload on port 8000

uv run poe lint                              # ruff linter
uv run poe format                            # ruff formatter
uv run poe test                              # pytest
uv run pytest -v path/to/test.py            # single test file
```
Swagger UI: `http://localhost:8000/docs`

### admin-front (`admin-front/`)
```bash
cd admin-front
pnpm install
cp .env.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
pnpm dev                     # http://localhost:3000

pnpm lint
pnpm format
pnpm knip    # dead code analysis
```

---

## Deployment

모든 프로덕션 배포는 `deploy/`에서 관리합니다.

### 최초 배포 준비
```bash
# orchestrator-server env 파일 (platform-server와 JWT_SECRET_KEY, POSTGRES_* 공유)
cp orchestrator-server/.env.example orchestrator-server/.env.staging
# admin-front 빌드 env 파일
cp admin-front/.env.example admin-front/.env.production
```
> `deploy.sh`는 `orchestrator-server/.env.$ENV`와 `admin-front/.env.production`의 존재를 확인하고,
> `docker compose --env-file orchestrator-server/.env.$ENV`로 기동합니다.

### 배포 / 중지 / 로그
```bash
./deploy/deploy.sh staging      # 또는 production

./deploy/stop.sh staging

# 서비스별 로그
./deploy/logs.sh platform       # Spring Boot (인증·사용자)
./deploy/logs.sh app            # FastAPI (LLM·RAG)
./deploy/logs.sh llm-admin      # Next.js
./deploy/logs.sh nginx          # Nginx
```

### 포트 맵

| Port | Service |
|------|---------|
| 8060 | Nginx (단일 공개 진입점) |
| 8063 | Prometheus |
| 8064 | Grafana |
| 8065 | cAdvisor |
| 8066 | PostgreSQL (호스트 노출) |
| 8067 | Langfuse UI |

> `platform-server(:8080)`, `orchestrator-server(:8000)`, `admin-front(:3000)`은 내부 네트워크 전용 — Nginx를 통해서만 접근.

### 단일 서비스 재빌드
```bash
cd deploy
APP_ENV=staging docker compose --env-file ../orchestrator-server/.env.staging up -d --build platform
APP_ENV=staging docker compose --env-file ../orchestrator-server/.env.staging up -d --build app
APP_ENV=staging docker compose --env-file ../orchestrator-server/.env.staging up -d --build llm-admin
```

### DB 스키마 초기화
`deploy/postgres/init.sql`이 PostgreSQL 볼륨 최초 생성 시 자동 실행되어 `llmonl` 스키마와
**모든 테이블(platform + orchestrator)** 을 생성합니다. orchestrator-server는 startup에
`create_all`이 없으므로 새 테이블은 init.sql에 DDL을 추가해야 하며, **이미 생성된 볼륨의 DB**에는
수동 적용이 필요합니다: `docker exec -i orchestration-db psql -U postgres -d mydb < 파일.sql`.
초기 시드 데이터(관리자 계정 등)는 `deploy/postgres/seed.sql`을 수동 실행.

### Kubernetes 배포 (이중화)

`deploy/k8s/`에 HA 구성 매니페스트가 있습니다. 자세한 내용은 `deploy/k8s/README.md` 참고.

```bash
# 이미지 빌드 후 레지스트리 푸시, 그 뒤:
cd deploy/k8s/scripts
REGISTRY=your-registry.io/llm-platform TAG=v1.0 ./deploy.sh staging
./logs.sh orchestrator staging
./stop.sh staging
```

주요 이중화 구성: platform·orchestrator replicas:2 + HPA·PDB, CloudNativePG (primary+replica), Redis Sentinel, MinIO 4-pod distributed.

### MinIO 버킷 초기화 (최초 배포 1회)
```bash
docker exec minio mc alias set local http://localhost:9000 minio miniosecret
docker exec minio mc mb local/langfuse-events
docker exec minio mc mb local/langfuse-media
docker exec minio mc mb local/langfuse-exports
docker exec minio mc mb local/meeting-recordings   # 회의록 오디오 (app이 자동 생성하므로 선택)
```
> 회의록 오디오는 `app`이 MinIO(`meeting-recordings`)에 저장합니다(compose의 `MEETING_S3_*`). 버킷은 미존재 시 자동 생성됩니다.

---

## Service Boundaries

### platform-server가 소유하는 것
| 기능 | 엔드포인트 |
|------|-----------|
| 회원가입 / 로그인 / 토큰 갱신 | `POST /api/v1/auth/*` |
| 사용자 조회·수정 | `GET/PATCH /api/v1/users/*` |
| API 키 발급·폐기 | `GET/POST/DELETE /api/v1/api-keys/*` |
| LLM 모델 리소스 설정 | `GET/POST/PATCH/DELETE /api/v1/llm-resources/*` |

### orchestrator-server가 소유하는 것
| 기능 | 엔드포인트 |
|------|-----------|
| LLM 채팅 (SSE 스트리밍) | `POST /api/v1/chatbot/chat/stream` |
| AI 에이전트 | `/api/v1/agents/*` |
| RAG (문서 업로드·검색) | `/api/v1/rag/*` |
| 워크플로우 엔진 | `/api/v1/workflows/*` |
| 음성 평가 | `/api/v1/voice-evaluation/*` |
| 음성 회의록 (업로드·전사·화자분리·AI 요약·발행) | `/api/v1/meetings/*` |

---

## Common Troubleshooting

| 증상 | 확인 사항 |
|------|-----------|
| `platform` 컨테이너 재시작 반복 | `JWT_SECRET_KEY` 32자 이상인지, `POSTGRES_*` 설정 확인 |
| `app` 컨테이너 시작 안 됨 | `OPENAI_API_KEY` / `JWT_SECRET_KEY` env 파일 누락 |
| 401 Unauthorized | platform-server와 orchestrator-server의 `JWT_SECRET_KEY`가 다름 |
| DB 연결 거부 | `POSTGRES_HOST=db` (서비스명, `localhost` 아님) |
| platform SchemaValidationException | `llmonl` 스키마·테이블 미생성 — `deploy/postgres/init.sql` 실행 후 platform-server 테이블 수동 생성 필요 |
| CORS 오류 | `ALLOWED_ORIGINS`에 Nginx 주소(`http://<ip>:8060`) 포함 필요 |
| WebSocket 실패 | `NEXT_PUBLIC_WS_URL` 포트가 Nginx 포트(8060)와 일치해야 함 |
| Langfuse 시작 안 됨 | `docker compose ps clickhouse redis minio` — 모두 healthy여야 함 |
| Langfuse trace가 UI에 안 보임 | `langfuse-worker` 컨테이너가 실행 중인지 확인 — worker가 없으면 OTLP 수신은 되나 Redis 큐에서 ClickHouse로 처리 안 됨 (`./logs.sh langfuse-worker`) |
| Next.js 빌드 실패 | `admin/llm-admin/.env.production` 빌드 전 존재해야 함 |
| Docker 빌드 후 API URL이 localhost | `admin-front/.dockerignore`에 `.env.local` 포함 필요 — 없으면 `.env.local`이 `.env.production`을 빌드 시 덮어써 `NEXT_PUBLIC_API_URL`이 잘못 임베딩됨 |
| 회의록이 `SAVED`에서 멈추고 요약 없음 | 전사(STT)가 결과를 못 냄 — `OPENAI_API_KEY`(Whisper) 유효성 확인. 오디오 저장 자체는 성공 상태 |
| 회의 녹음 버튼이 권한 요청 없이 실패 | `getUserMedia`는 보안 컨텍스트 전용 — `http://<IP>:8060`이 아닌 `localhost` 또는 HTTPS로 접속해야 함 (파일 업로드는 제약 없음) |
| 회의록 화자분리가 단일 화자 | `AZURE_SPEECH_KEY`/`AZURE_SPEECH_REGION` 미설정 시 Whisper 폴백(화자분리 없음) |
