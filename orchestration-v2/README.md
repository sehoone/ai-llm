# LLM Orchestration Platform

LangGraph 기반 LLM 오케스트레이션 플랫폼. RAG, AI 에이전트, 워크플로우 엔진, 음성 평가를 하나의 스택으로 제공합니다.

## 서비스 구성

| 서비스 | 스택 | 역할 |
|--------|------|------|
| `orchestrator-server/` | Python 3.13, FastAPI, LangGraph | LLM 채팅·RAG·워크플로우·음성 평가 |
| `platform-server/` | Java 21, Spring Boot 3.4, Flyway | 인증·사용자·API 키·LLM 리소스 관리 |
| `admin-front/` | Next.js 16, TypeScript, pnpm | 관리자 대시보드 |
| `deploy/` | Docker Compose, Nginx | 프로덕션 배포 |

---

## 시스템 아키텍처

```
Browser / API Client
        │
        ▼
  :8060  Nginx (단일 진입점)
        │
        ├── /auth/*                     → Keycloak:8080  (OIDC 엔드포인트)
        │
        ├── /api/v1/voice-evaluation/ws/* → orchestrator-server:8000 (WebSocket)
        │
        ├── /api/*                      → platform-server:8080 (Spring Boot)
        │     ├── /api/v1/auth/*             직접 처리 (JWT 발급)
        │     ├── /api/v1/users/*            직접 처리
        │     ├── /api/v1/api-keys/*         직접 처리
        │     ├── /api/v1/llm-resources/*    직접 처리
        │     └── 나머지 /api/*         → orchestrator-server:8000 내부 프록시
        │                                    ├── /api/v1/chatbot     LLM 채팅 (SSE)
        │                                    ├── /api/v1/agents      AI 에이전트
        │                                    ├── /api/v1/rag         RAG 파이프라인
        │                                    ├── /api/v1/workflows   DAG 워크플로우
        │                                    └── /api/v1/voice-evaluation 음성 평가
        │
        └── /*                          → admin-front:3000 (Next.js)

JWT 흐름
  Client → POST /api/v1/auth/login → platform-server 발급 (HS256)
                                   → orchestrator-server 동일 JWT_SECRET_KEY로 검증

PostgreSQL + pgvector  (schema: llmonl)
  ├── platform-server: users, api_key, refresh_token, llm_resource  (Flyway 관리)
  └── orchestrator-server: session, gpt_chat_message, rag_embedding, workflow, ...  (SQLModel 자동 생성)

Observability
  ├── Prometheus  :8063  ← FastAPI /metrics + cAdvisor
  ├── Grafana     :8064  ← LLM Inference Latency 대시보드 자동 프로비저닝
  └── cAdvisor    :8065  ← 컨테이너 리소스 메트릭

Langfuse v3  :8067  (LLM 트레이싱)
  ├── ClickHouse  ← 트레이스 데이터
  ├── Redis       ← 작업 큐
  └── MinIO       ← 이벤트·미디어 blob

Keycloak  :8068  (OAuth2/OIDC — AUTH_MODE=keycloak 시 활성화)
```

---

## 포트 맵

| 포트 | 서비스 | 비고 |
|------|--------|------|
| **8060** | Nginx | 공개 단일 진입점 |
| **8063** | Prometheus | 메트릭 수집 UI |
| **8064** | Grafana | 대시보드 |
| **8065** | cAdvisor | 컨테이너 모니터링 |
| **8066** | PostgreSQL | 호스트 직접 접속용 (개발) |
| **8067** | Langfuse | LLM 트레이싱 UI |
| **8068** | Keycloak | OAuth2 관리 콘솔 |
| 내부전용 | platform-server:8080, orchestrator-server:8000, admin-front:3000 | Nginx 경유 접근 |

---

## 인증 모드

`AUTH_MODE` 환경변수로 두 가지 인증 방식을 선택합니다.

| 모드 | 설명 | 기본 적용 환경 |
|------|------|---------------|
| `jwt` | platform-server가 HS256 JWT 발급, orchestrator-server가 동일 시크릿으로 검증 | `development`, `test` |
| `keycloak` | Keycloak이 RS256 JWT 발급, orchestrator-server가 JWKS로 검증 | `staging`, `production` |

> `.env` 파일에 `AUTH_MODE=jwt` 또는 `AUTH_MODE=keycloak`을 명시하면 환경 기본값을 덮어씁니다.

---

## 로컬 개발 환경

### 사전 요구사항

- Java 21, Gradle
- Python 3.13+, [uv](https://docs.astral.sh/uv/)
- Node.js 20+, pnpm
- PostgreSQL (또는 Docker)

### platform-server

```powershell
cd platform-server
cp .env.example .env.local   # JWT_SECRET_KEY (32자+), POSTGRES_* 설정
$env:APP_ENV='local'; ./gradlew bootRun
```

Swagger UI: `http://localhost:8080/swagger-ui/index.html`

### orchestrator-server

```powershell
cd orchestrator-server
uv sync
cp .env.example .env.development   # OPENAI_API_KEY, JWT_SECRET_KEY 등 설정
$env:APP_ENV='development'; uv run uvicorn src.main:app --reload --port 8000
```

Swagger UI: `http://localhost:8000/docs`

### admin-front

```bash
cd admin-front
pnpm install
cp .env.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
pnpm dev                     # http://localhost:3000
```

> **중요**: `JWT_SECRET_KEY`는 platform-server와 orchestrator-server가 반드시 동일한 값이어야 합니다.

---

## 배포

모든 배포는 `deploy/` 디렉토리에서 관리합니다. Docker Compose로 14개 서비스를 한 번에 기동합니다.

### 1단계 — 환경 파일 준비

```bash
# orchestrator-server 환경 파일 (platform-server와 공유)
cp orchestrator-server/.env.example orchestrator-server/.env.staging

# admin-front 빌드 환경 파일
cp admin-front/.env.example admin-front/.env.production
```

#### orchestrator-server/.env.staging 필수 항목

```env
APP_ENV=staging

# LLM
OPENAI_API_KEY=sk-proj-...

# JWT (32자 이상, openssl rand -hex 32 로 생성)
JWT_SECRET_KEY=<랜덤 시크릿>

# 인증 모드
AUTH_MODE=keycloak   # staging/production은 keycloak 권장

# DB (Docker 내부 서비스명 사용)
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=mydb
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<강력한 패스워드>
POSTGRES_SCHEMA=llmonl

# CORS
ALLOWED_ORIGINS="http://<서버IP>:8060"

# Langfuse (배포 후 UI에서 키 발급 → 재입력)
LANGFUSE_HOST=http://langfuse:3000
LANGFUSE_NEXTAUTH_SECRET=<openssl rand -hex 32>
LANGFUSE_SALT=<openssl rand -hex 16>
LANGFUSE_ENCRYPTION_KEY=<openssl rand -hex 32>

# Grafana
GRAFANA_ADMIN_PASSWORD=<강력한 패스워드>
```

#### admin-front/.env.production 필수 항목

```env
# 비워두면 Nginx(/api/*) 경유 (권장)
NEXT_PUBLIC_API_URL=

# WebSocket — Nginx 포트(8060) 사용
NEXT_PUBLIC_WS_URL=ws://<서버IP>:8060/api/v1/voice-evaluation/ws/conversation

# Auth 모드 표시 배너용
NEXT_PUBLIC_AUTH_MODE=keycloak
```

### 2단계 — 배포 실행

```bash
./deploy/deploy.sh staging      # staging
./deploy/deploy.sh production   # production (기본값)
```

### 3단계 — MinIO 버킷 초기화 (최초 1회)

```bash
docker exec minio mc alias set local http://localhost:9000 minio miniosecret
docker exec minio mc mb local/langfuse-events
docker exec minio mc mb local/langfuse-media
docker exec minio mc mb local/langfuse-exports
```

### 4단계 — Langfuse 초기 설정

`http://<서버IP>:8067` 에서 계정 생성 후 **API Keys** 메뉴에서 키를 발급합니다.
발급한 `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`를 `.env.staging`에 추가하고 app만 재배포합니다.

```bash
cd deploy
APP_ENV=staging docker compose --env-file ../orchestrator-server/.env.staging up -d --build app
```

### 접속 주소

| URL | 서비스 |
|-----|--------|
| `http://<서버IP>:8060` | 관리자 UI |
| `http://<서버IP>:8060/api/v1/auth/swagger-ui` | platform-server Swagger |
| `http://<서버IP>:8067` | Langfuse |
| `http://<서버IP>:8063` | Prometheus |
| `http://<서버IP>:8064` | Grafana (admin / `GRAFANA_ADMIN_PASSWORD`) |
| `http://<서버IP>:8065` | cAdvisor |
| `http://<서버IP>:8068` | Keycloak 관리 콘솔 |

---

## 운영 명령

```bash
# 서비스 중지
./deploy/stop.sh staging

# 볼륨까지 삭제 (DB 데이터 포함 — 주의)
cd deploy && docker compose down -v

# 특정 서비스 재빌드
cd deploy
APP_ENV=staging docker compose --env-file ../orchestrator-server/.env.staging up -d --build app       # FastAPI
APP_ENV=staging docker compose --env-file ../orchestrator-server/.env.staging up -d --build platform  # Spring Boot
APP_ENV=staging docker compose --env-file ../orchestrator-server/.env.staging up -d --build llm-admin # Next.js

# 로그 확인
./deploy/logs.sh app          # FastAPI
./deploy/logs.sh platform     # Spring Boot
./deploy/logs.sh llm-admin    # Next.js
./deploy/logs.sh nginx
./deploy/logs.sh langfuse
./deploy/logs.sh db

# 컨테이너 상태
cd deploy && docker compose ps
```

---

## 트러블슈팅

| 증상 | 확인 사항 |
|------|-----------|
| `platform` 컨테이너 재시작 반복 | `JWT_SECRET_KEY` 32자 이상인지 확인 |
| `app` 컨테이너 시작 안 됨 | `OPENAI_API_KEY` / `JWT_SECRET_KEY` 누락 여부 확인 |
| 401 Unauthorized | platform-server와 orchestrator-server의 `JWT_SECRET_KEY` 불일치 |
| DB 연결 거부 | `POSTGRES_HOST=db` (서비스명) 사용 — `localhost` 아님 |
| CORS 오류 | `ALLOWED_ORIGINS`에 Nginx 주소(`http://<IP>:8060`) 포함 필요 |
| WebSocket 연결 실패 | `NEXT_PUBLIC_WS_URL` 포트가 Nginx 포트(8060)와 일치해야 함 |
| Langfuse 시작 안 됨 | ClickHouse·Redis·MinIO가 모두 healthy인지 확인 → MinIO 버킷 초기화 필요할 수 있음 |
| Next.js 빌드 실패 | `admin-front/.env.production` 파일이 빌드 전 존재해야 함 |
| Flyway 마이그레이션 오류 | `llmonl` 스키마는 `deploy/postgres/init.sql`에서 자동 생성됨 |
| `AUTH_MODE=keycloak` 인데 Keycloak 미기동 | `docker compose ps keycloak` 확인; start_period 90s 대기 |

---

## 디렉토리 구조

```
orchestration-v2/
├── orchestrator-server/   # FastAPI (Python)
├── platform-server/       # Spring Boot (Java)
├── admin-front/           # Next.js (TypeScript)
└── deploy/
    ├── docker-compose.yml
    ├── deploy.sh
    ├── stop.sh
    ├── logs.sh
    ├── nginx/
    │   └── nginx.conf
    ├── postgres/
    │   └── init.sql       # llmonl·keycloak 스키마 생성
    ├── keycloak/
    │   └── realm-import.json
    ├── clickhouse/
    │   └── config.xml
    ├── prometheus/
    │   └── prometheus.yml
    └── grafana/
        ├── datasources/
        └── dashboards/    # LLM Inference Latency 대시보드 자동 프로비저닝
```

각 서비스의 상세 가이드는 해당 디렉토리의 `CLAUDE.md`를 참고하세요.
