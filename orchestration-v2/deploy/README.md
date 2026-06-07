# Deploy

`orchestration` (FastAPI 백엔드)와 `llm-admin` (Next.js 프론트엔드)을 한 번에 Docker로 배포합니다.
Nginx가 단일 진입점(:8060)으로 두 서비스를 라우팅합니다.

## 디렉토리 구조

```
deploy/
├── docker-compose.yml        # 전체 서비스 정의
├── nginx/
│   └── nginx.conf            # 리버스 프록시 설정
├── clickhouse/
│   └── config.xml            # ClickHouse 단일 노드 클러스터 설정 (Langfuse v3용)
├── deploy.sh                 # 배포 스크립트
├── stop.sh                   # 중지 스크립트
└── logs.sh                   # 로그 조회 스크립트

orchestration/
├── prometheus/
│   └── prometheus.yml        # Prometheus 스크랩 설정 (FastAPI + cAdvisor)
└── grafana/
    ├── datasources/
    │   └── datasource.yml    # Prometheus 데이터소스 자동 프로비저닝
    └── dashboards/
        ├── dashboards.yml    # 대시보드 프로바이더 설정
        └── json/
            └── llm_latency.json  # LLM Inference Latency 대시보드
```

## 서비스 구성

| 서비스 | 이미지 | 포트 | 설명 |
|--------|--------|------|------|
| nginx | nginx:alpine | `8060` | 프론트엔드 / API 단일 진입점 |
| llm-admin | (빌드) | - | Next.js 프론트엔드 |
| app | (빌드) | - | FastAPI 백엔드 |
| db | pgvector/pgvector:pg16 | `8066` | PostgreSQL + pgvector |
| langfuse | langfuse/langfuse:3 | `8067` | LLM 추적/관찰 UI |
| clickhouse | clickhouse-server:24.1 | - | Langfuse v3 분석 DB |
| redis | redis:7-alpine | - | Langfuse v3 작업 큐 |
| minio | minio/minio | - | Langfuse v3 오브젝트 스토리지 |
| prometheus | prom/prometheus | `8063` | 메트릭 수집 UI |
| grafana | grafana/grafana | `8064` | 메트릭 시각화 대시보드 |
| cadvisor | cadvisor:latest | `8065` | 컨테이너 리소스 모니터링 |

### 트래픽 흐름

```
외부 요청
    │
    ▼
:8060 (nginx)
    ├── /api/*  →  orchestration:8000  (FastAPI)
    └── /*      →  llm-admin:3000      (Next.js)

모니터링
    ├── Prometheus :8063  ←  FastAPI /metrics + cAdvisor
    ├── Grafana    :8064  ←  Prometheus (대시보드 자동 프로비저닝)
    └── cAdvisor   :8065  ←  Docker 컨테이너 리소스 메트릭

Langfuse v3 내부 연결
    ├── ClickHouse  ←  Langfuse (trace 데이터 저장)
    ├── Redis       ←  Langfuse (작업 큐)
    └── MinIO       ←  Langfuse (이벤트/미디어 파일)
```

---

## 배포 절차

### 1. 환경변수 파일 준비

#### API 서버 (orchestrator-server)

staging 환경:

```bash
cp orchestrator-server/.env.example orchestrator-server/.env.staging
```

`orchestrator-server/.env.staging` 주요 항목 편집:

```env
APP_ENV=staging

# LLM (필수)
OPENAI_API_KEY=sk-proj-...

# JWT (반드시 랜덤 값으로 생성)
JWT_SECRET_KEY=<아래 명령으로 생성>

# DB 연결 (Docker 내부 서비스명 사용)
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=mydb
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<강력한 패스워드>
POSTGRES_SCHEMA=llmonl

# CORS (실제 서버 IP/도메인 입력)
ALLOWED_ORIGINS="http://localhost:3000,http://localhost:8000,http://<서버IP>:8060"

# Langfuse (컨테이너 내부 주소 — 변경 불필요)
LANGFUSE_HOST=http://langfuse:3000
LANGFUSE_ENABLED=true

# Langfuse 서버 자체 설정 (배포 전 반드시 변경)
LANGFUSE_NEXTAUTH_SECRET=<아래 명령으로 생성>
LANGFUSE_SALT=<랜덤 문자열>
LANGFUSE_ENCRYPTION_KEY=<64자 hex — 아래 명령으로 생성>

# Grafana 관리자 패스워드
GRAFANA_ADMIN_PASSWORD=<강력한 패스워드>

DEBUG=false
```

시크릿 키 생성 명령:

```bash
# JWT_SECRET_KEY, LANGFUSE_NEXTAUTH_SECRET, LANGFUSE_SALT
openssl rand -hex 32

# LANGFUSE_ENCRYPTION_KEY (정확히 64자 hex)
openssl rand -hex 32
```

#### 프론트엔드 (llm-admin)

```bash
cp admin/llm-admin/.env.example admin/llm-admin/.env.production
```

`admin/llm-admin/.env.production` 편집:

```env
# 클라이언트에서 API 호출 — 비워두면 Nginx(/api/*) 경유 (권장)
NEXT_PUBLIC_API_URL=

# WebSocket URL — 서버 IP와 Nginx 포트(8060) 사용
NEXT_PUBLIC_WS_URL=ws://<서버IP>:8060/api/v1/voice-evaluation/ws/conversation
```

> **참고:** 프론트엔드는 환경 구분 없이 `.env.production` 파일 하나만 사용합니다.

### 2. 배포 실행

```bash
# staging 배포
./deploy/deploy.sh staging

# production 배포 (기본값)
./deploy/deploy.sh
./deploy/deploy.sh production
```

### 3. 시드 데이터 적용 (최초 1회)

DB 볼륨이 처음 생성된 경우, 기본 계정과 LLM 리소스를 삽입합니다.

```bash
docker exec -i db psql -U postgres -d mydb < deploy/postgres/seed.sql
```

> **기본 계정** (비밀번호 반드시 변경):
> - `superadmin@example.com` / `admin1234!`
> - `admin@example.com` / `admin1234!`
> - `user1@example.com` / `user1234!`
>
> **LLM 리소스** (`llm_resource` 테이블): GPT-4o, GPT-4o-mini, text-embedding-3-small 가 `REPLACE_WITH_OPENAI_API_KEY` 플레이스홀더로 삽입됩니다.
> 실제 API 키는 seed.sql 실행 전에 파일을 편집하거나, 실행 후 관리 UI에서 직접 수정하세요.

### 4. Langfuse MinIO 버킷 초기화 (최초 1회)

**최초 배포 시에만** 아래 명령으로 MinIO 버킷을 생성합니다.

```bash
docker exec minio mc alias set local http://localhost:9000 minio miniosecret
docker exec minio mc mb local/langfuse-events
docker exec minio mc mb local/langfuse-media
docker exec minio mc mb local/langfuse-exports
```

> 재배포(코드 변경) 시에는 볼륨이 유지되므로 이 단계를 건너뜁니다.

### 5. 접근 주소 확인

빌드 및 컨테이너 기동 완료 후:

- 프론트엔드: `http://<서버IP>:8060`
- API: `http://<서버IP>:8060/api`
- Langfuse: `http://<서버IP>:8067`
- Prometheus: `http://<서버IP>:8063`
- Grafana: `http://<서버IP>:8064`
- cAdvisor: `http://<서버IP>:8065`

#### Langfuse 초기 설정

`http://<서버IP>:8067` 에서 계정 생성 후 **API Keys** 메뉴에서 Public/Secret 키를 발급합니다.
발급한 키를 `.env.staging`에 입력하고 `orchestration-app`만 재배포합니다:

```bash
cd deploy
APP_ENV=staging docker compose --env-file ../orchestrator-server/.env.staging up -d --build app
```

#### Grafana 초기 로그인

기본 계정: `admin` / `admin` (또는 `GRAFANA_ADMIN_PASSWORD` 설정값)
기동 시 **LLM Inference Latency** 대시보드와 Prometheus 데이터소스가 자동 프로비저닝됩니다.

---

## 중지

```bash
./deploy/stop.sh staging
./deploy/stop.sh production   # 기본값
```

볼륨까지 삭제하려면 (DB, Langfuse 데이터 포함):

```bash
cd deploy
docker compose down -v
```

---

## 로그 조회

```bash
# 전체 서비스 로그
./deploy/logs.sh

# 특정 서비스 로그
./deploy/logs.sh app          # FastAPI
./deploy/logs.sh llm-admin    # Next.js
./deploy/logs.sh nginx        # Nginx
./deploy/logs.sh db           # PostgreSQL
./deploy/logs.sh langfuse     # Langfuse
./deploy/logs.sh clickhouse   # ClickHouse
./deploy/logs.sh redis        # Redis
./deploy/logs.sh minio        # MinIO
./deploy/logs.sh prometheus   # Prometheus
./deploy/logs.sh grafana      # Grafana
./deploy/logs.sh cadvisor     # cAdvisor

# 환경 지정
./deploy/logs.sh app staging
```

---

## 서비스 상태 확인

```bash
cd deploy
docker compose ps
```

---

## 재배포 (코드 변경 후)

```bash
# 전체 재빌드
./deploy/deploy.sh staging

# 특정 서비스만 재빌드
cd deploy
APP_ENV=staging docker compose --env-file ../orchestrator-server/.env.staging up -d --build app
APP_ENV=staging docker compose --env-file ../orchestrator-server/.env.staging up -d --build llm-admin
```

---

## 트러블슈팅

### orchestration-app이 시작되지 않음

`docker compose logs app`으로 확인합니다.
가장 흔한 원인: `OPENAI_API_KEY` 또는 `JWT_SECRET_KEY`가 비어 있음.

```bash
docker compose logs app --tail=20
```

### LangGraph 채팅 상태가 저장되지 않음 (`relation "checkpoints" does not exist`)

`deploy/postgres/init.sql`에 LangGraph 체크포인터 테이블이 포함되어 있습니다.
DB 볼륨이 `init.sql` 추가 이전에 생성된 경우 테이블이 없을 수 있습니다.

```bash
docker exec -i db psql -U postgres -d mydb << 'EOF'
CREATE TABLE IF NOT EXISTS llmonl.checkpoint_migrations (v INTEGER PRIMARY KEY);
CREATE TABLE IF NOT EXISTS llmonl.checkpoints (
    thread_id TEXT NOT NULL, checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL, parent_checkpoint_id TEXT,
    type TEXT, checkpoint JSONB NOT NULL, metadata JSONB NOT NULL DEFAULT '{}',
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);
CREATE TABLE IF NOT EXISTS llmonl.checkpoint_blobs (
    thread_id TEXT NOT NULL, checkpoint_ns TEXT NOT NULL DEFAULT '',
    channel TEXT NOT NULL, version TEXT NOT NULL, type TEXT NOT NULL, blob BYTEA,
    PRIMARY KEY (thread_id, checkpoint_ns, channel, version)
);
CREATE TABLE IF NOT EXISTS llmonl.checkpoint_writes (
    thread_id TEXT NOT NULL, checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL, task_id TEXT NOT NULL, idx INTEGER NOT NULL,
    channel TEXT NOT NULL, type TEXT, blob BYTEA NOT NULL,
    task_path TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);
CREATE INDEX IF NOT EXISTS checkpoints_thread_id_idx ON llmonl.checkpoints(thread_id);
CREATE INDEX IF NOT EXISTS checkpoint_blobs_thread_id_idx ON llmonl.checkpoint_blobs(thread_id);
CREATE INDEX IF NOT EXISTS checkpoint_writes_thread_id_idx ON llmonl.checkpoint_writes(thread_id);
INSERT INTO llmonl.checkpoint_migrations(v)
SELECT s.v FROM generate_series(0,9) AS s(v) ON CONFLICT(v) DO NOTHING;
EOF
```

테이블 생성 후 `app` 컨테이너를 재시작합니다:

```bash
docker compose restart app
```

### DB 연결 실패

`.env.staging`에서 아래 값을 확인합니다.

```env
POSTGRES_HOST=db       # Docker 서비스명 (localhost 아님)
POSTGRES_PORT=5432     # 컨테이너 내부 포트 (호스트 노출 포트 8066 아님)
```

### CORS 오류

`ALLOWED_ORIGINS`에 실제 접근 주소(IP + 포트)가 포함되어 있는지 확인합니다.

```env
ALLOWED_ORIGINS="http://<서버IP>:8060"
```

### WebSocket 연결 실패

`NEXT_PUBLIC_WS_URL`의 포트가 Nginx 포트(`8060`)와 일치하는지 확인합니다.

```env
NEXT_PUBLIC_WS_URL=ws://<서버IP>:8060/api/v1/voice-evaluation/ws/conversation
```

### Langfuse가 시작되지 않음

ClickHouse, Redis, MinIO가 모두 healthy 상태인지 확인합니다.

```bash
docker compose ps clickhouse redis minio
```

MinIO 버킷이 없을 경우 [버킷 초기화](#3-langfuse-minio-버킷-초기화-최초-1회) 단계를 수행합니다.

### Next.js 빌드 실패

`admin/llm-admin/.env.production` 파일이 존재하는지 확인합니다.

```bash
ls admin/llm-admin/.env.production
```

### Windows 환경에서 빌드 시 `no such file or directory` 오류

셸 스크립트의 CRLF 라인 엔딩 문제입니다. Dockerfile에 이미 자동 변환이 포함되어 있으므로
별도 조치 없이 재빌드하면 해결됩니다.

```bash
./deploy/deploy.sh staging
```
