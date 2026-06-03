# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Workspace Structure

관심사 분리(Separation of Concerns) 원칙으로 구성된 LLM 오케스트레이션 플랫폼 monorepo.

| Directory | Stack | Description |
|-----------|-------|-------------|
| `orchestrator-server/` | Python 3.13+, FastAPI, LangGraph | LLM 채팅·RAG·워크플로우 엔진 |
| `platform-server/` | Java 21, Spring Boot 3.4, Flyway | 인증·사용자·LLM 리소스 관리 |
| `admin-front/` | Next.js 16, TypeScript, pnpm | 관리자 프론트엔드 |
| `deploy/` | Docker Compose, Nginx | 프로덕션 배포 |

모듈 상세: `orchestrator-server/CLAUDE.md`, `admin-front/CLAUDE.md`

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
        │     └── /voice-evaluation 음성 평가
        │
        └── /*                      → admin-front:3000 (Next.js)

JWT 흐름
  Client → POST /api/v1/auth/login → platform-server 발급 (HS256)
                                   → orchestrator-server 동일 JWT_SECRET_KEY로 검증

PostgreSQL + pgvector  (schema: llmonl)
  ├── platform-server 소유: users, api_key, refresh_token, llm_resource
  │   └── Flyway 마이그레이션 (flyway_platform_history 테이블)
  └── orchestrator-server 소유: session, gpt_chat_message, rag_embedding, workflow, ...
      └── SQLModel ORM 자동 생성

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

### platform-server (`platform-server/`)
```powershell
cd platform-server
cp .env.example .env.local   # JWT_SECRET_KEY, POSTGRES_* 설정
# Gradle wrapper 없으면: gradle wrapper (Gradle 전역 설치 필요)
$env:APP_ENV='local'; ./gradlew bootRun
```
Swagger UI: `http://localhost:8080/swagger-ui/index.html`

> **중요**: `JWT_SECRET_KEY`는 orchestrator-server와 반드시 동일한 값이어야 합니다.

### orchestrator-server (`orchestrator-server/`)
```powershell
cd orchestrator-server
uv sync
cp .env.example .env.development   # fill in secrets
$env:APP_ENV='development'; uv run uvicorn src.main:app --reload --port 8000
```
Swagger UI: `http://localhost:8000/docs`

### admin-front (`admin-front/`)
```bash
cd admin-front
pnpm install
cp .env.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
pnpm dev                     # http://localhost:3000
```

---

## Deployment

모든 프로덕션 배포는 `deploy/`에서 관리합니다.

### 최초 배포 준비
```bash
# orchestrator-server env 파일 (platform-server와 JWT_SECRET_KEY, POSTGRES_* 공유)
cp orchestrator-server/.env.example ../orchestration/.env.staging
# admin-front env 파일
cp admin-front/.env.example ../admin/llm-admin/.env.production

# platform-server는 orchestrator-server env 파일을 자동으로 공유
# 별도 설정이 필요한 경우에만 생성:
# cp platform-server/.env.example platform-server/.env.staging
```

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
# platform-server (Spring Boot)
APP_ENV=staging docker compose --env-file ../orchestration/.env.staging up -d --build platform

# orchestrator-server (FastAPI)
APP_ENV=staging docker compose --env-file ../orchestration/.env.staging up -d --build app

# admin-front (Next.js)
APP_ENV=staging docker compose --env-file ../orchestration/.env.staging up -d --build llm-admin
```

### MinIO 버킷 초기화 (최초 배포 1회)
```bash
docker exec minio mc alias set local http://localhost:9000 minio miniosecret
docker exec minio mc mb local/langfuse-events
docker exec minio mc mb local/langfuse-media
docker exec minio mc mb local/langfuse-exports
```

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

---

## Common Troubleshooting

| 증상 | 확인 사항 |
|------|-----------|
| `platform` 컨테이너 재시작 반복 | `JWT_SECRET_KEY` 32자 이상인지, `POSTGRES_*` 설정 확인 |
| `app` 컨테이너 시작 안 됨 | `OPENAI_API_KEY` / `JWT_SECRET_KEY` env 파일 누락 |
| 401 Unauthorized | platform-server와 orchestrator-server의 `JWT_SECRET_KEY`가 다름 |
| DB 연결 거부 | `POSTGRES_HOST=db` (서비스명, `localhost` 아님) |
| CORS 오류 | `ALLOWED_ORIGINS`에 Nginx 주소(`http://<ip>:8060`) 포함 필요 |
| WebSocket 실패 | `NEXT_PUBLIC_WS_URL` 포트가 Nginx 포트(8060)와 일치해야 함 |
| Langfuse 시작 안 됨 | `docker compose ps clickhouse redis minio` — 모두 healthy여야 함 |
| Next.js 빌드 실패 | `admin/llm-admin/.env.production` 빌드 전 존재해야 함 |
| platform Flyway 오류 | `llmonl` 스키마가 없으면 Flyway가 자동 생성 (`create-schemas: true`) |
