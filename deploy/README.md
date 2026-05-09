# Deploy

`orchestration` (FastAPI 백엔드)와 `llm-admin` (Next.js 프론트엔드)을 한 번에 Docker로 배포합니다.
Nginx가 단일 진입점(:8060)으로 두 서비스를 라우팅합니다.

## 디렉토리 구조

```
deploy/
├── docker-compose.yml   # 전체 서비스 정의
├── nginx/
│   └── nginx.conf       # 리버스 프록시 설정
├── deploy.sh            # 배포 스크립트
├── stop.sh              # 중지 스크립트
└── logs.sh              # 로그 조회 스크립트

orchestration/
├── prometheus/
│   └── prometheus.yml   # Prometheus 스크랩 설정 (FastAPI + cAdvisor)
└── grafana/
    ├── datasources/
    │   └── datasource.yml   # Prometheus 데이터소스 자동 프로비저닝
    └── dashboards/
        ├── dashboards.yml   # 대시보드 프로바이더 설정
        └── json/
            └── llm_latency.json   # LLM Inference Latency 대시보드
```

## 노출 포트

| 포트 | 서비스 | 설명 |
|------|--------|------|
| `8060` | nginx | 프론트엔드 / API 단일 진입점 |
| `8063` | prometheus | 메트릭 수집 UI |
| `8064` | grafana | 메트릭 시각화 대시보드 |
| `8065` | cadvisor | 컨테이너 리소스 모니터링 |
| `8066` | db | PostgreSQL 외부 노출 포트 |
| `8067` | langfuse | LLM 추적/관찰 UI |

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
```

---

## 배포 절차

### 1. 환경변수 파일 준비

#### API 서버 (orchestration)

```bash
cp orchestration/.env.example orchestration/.env.production
```

`orchestration/.env.production` 주요 항목 편집:

```env
# DB 연결 (Docker 내부 서비스명 사용)
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=mydb
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<강력한 패스워드>
POSTGRES_SCHEMA=llmonl

# JWT (반드시 랜덤 값 생성)
JWT_SECRET_KEY=<아래 명령으로 생성>

# CORS (실제 서버 IP/도메인 입력)
ALLOWED_ORIGINS="http://localhost:3000,http://localhost:8000,http://<서버IP>:8060"

# 프로덕션에서 비활성화
DEBUG=false
```

JWT 시크릿 키 생성:

```bash
openssl rand -hex 32
```

#### 프론트엔드 (llm-admin)

```bash
cp admin/llm-admin/.env.example admin/llm-admin/.env.production
```

`admin/llm-admin/.env.production` 주요 항목 편집:

```env
# 클라이언트에서 API 호출 — 비워두면 Nginx(/api/*) 경유 (권장)
NEXT_PUBLIC_API_URL=

# WebSocket URL — 서버 IP와 Nginx 포트(8060) 사용
NEXT_PUBLIC_WS_URL=ws://<서버IP>:8060/api/v1/voice-evaluation/ws/conversation
```

### 2. 배포 실행

```bash
# production 배포 (기본값)
./deploy/deploy.sh

# 환경 지정
./deploy/deploy.sh production
./deploy/deploy.sh staging
./deploy/deploy.sh development
```

빌드 및 컨테이너 기동이 완료되면 아래 주소로 접근 가능합니다.

- 프론트엔드: `http://<서버IP>:8060`
- API: `http://<서버IP>:8060/api`
- Prometheus: `http://<서버IP>:8063`
- Grafana: `http://<서버IP>:8064`
- cAdvisor: `http://<서버IP>:8065`
- Langfuse: `http://<서버IP>:8067`

#### Grafana 초기 로그인

기본 계정: `admin` / `admin` (`.env.production`에 `GRAFANA_ADMIN_PASSWORD` 설정 권장)

```env
# orchestration/.env.production
GRAFANA_ADMIN_PASSWORD=<강력한 패스워드>
```

기동 시 **LLM Inference Latency** 대시보드와 Prometheus 데이터소스가 자동으로 프로비저닝됩니다.

---

## 중지

```bash
./deploy/stop.sh

# 환경 지정
./deploy/stop.sh production
```

볼륨까지 삭제하려면:

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
# 변경된 서비스만 재빌드 후 재시작
./deploy/deploy.sh

# 특정 서비스만 재빌드
cd deploy
APP_ENV=production docker compose up -d --build app
APP_ENV=production docker compose up -d --build llm-admin
```

---

## 트러블슈팅

### DB 연결 실패

`orchestration/.env.production`에서 아래 값을 확인합니다.

```env
POSTGRES_HOST=db       # Docker 서비스명 (localhost 아님)
POSTGRES_PORT=5432     # 컨테이너 내부 포트 (호스트 노출 포트 아님)
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

### Next.js 빌드 실패

`admin/llm-admin/.env.production` 파일이 존재하는지 확인합니다.

```bash
ls admin/llm-admin/.env.production
```
