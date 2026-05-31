# Deploy Guide

## 구조

```
deploy/
├── Dockerfile
├── dev/
│   ├── docker-compose.yml
│   └── .env.example
├── stg/
│   ├── docker-compose.yml
│   └── .env.example
├── prod/
│   ├── docker-compose.yml
│   └── .env.example
├── monitor/
│   ├── docker-compose.yml
│   ├── .env.example
│   ├── prometheus/prometheus.yml
│   ├── loki/loki-config.yml
│   ├── promtail/promtail-config.yml
│   └── grafana/provisioning/
│       ├── datasources/datasources.yml
│       └── dashboards/dashboards.yml
└── README.md
```

**요구사항:** Docker 24+, Docker Compose v2+

---

## dev

`ddl-auto: validate` · PostgreSQL 포함

```bash
cd deploy/dev
cp .env.example .env
docker compose up -d
docker compose logs -f app
docker compose down
```

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `DB_NAME` | `sample_db` | DB명 |
| `DB_USERNAME` | `postgres` | DB 사용자 |
| `DB_PASSWORD` | `postgres` | DB 비밀번호 |
| `API_KEY` | `change-me-in-dev` | X-API-Key 인증 키 |
| `TODO_API_URL` | `https://jsonplaceholder.typicode.com` | 외부 API URL |
| `PORT` | `8080` | 앱 포트 |

---

## stg

`ddl-auto: none` · 모든 환경변수 필수 · 네트워크: `spring-ai-mcp-stg-net`

```bash
cd deploy/stg
cp .env.example .env && vi .env   # 빈 값 없이 채울 것
docker compose up -d
docker compose down               # 볼륨 유지
docker compose down -v            # 볼륨 삭제
```

| 변수 | 설명 |
|------|------|
| `DB_NAME` | DB명 |
| `DB_USERNAME` | DB 사용자 |
| `DB_PASSWORD` | DB 비밀번호 |
| `API_KEY` | X-API-Key 인증 키 (32자 이상 권장) |
| `TODO_API_URL` | 외부 API URL |
| `PORT` | 앱 포트 (기본값: `8080`) |

---

## prod

`ddl-auto: none` · 모든 환경변수 필수

```bash
cd deploy/prod
cp .env.example .env && vi .env   # 빈 값 없이 채울 것
docker compose up -d
docker compose down               # 볼륨 유지
docker compose down -v            # 볼륨 삭제
```

| 변수 | 설명 |
|------|------|
| `DB_NAME` | DB명 |
| `DB_USERNAME` | DB 사용자 |
| `DB_PASSWORD` | DB 비밀번호 |
| `API_KEY` | X-API-Key 인증 키 |
| `TODO_API_URL` | 외부 API URL |
| `PORT` | 앱 포트 (기본값: `8080`) |

---

## monitor

Prometheus + Grafana + Loki + Promtail

**선행 조건:** dev 또는 prod가 먼저 실행 중이어야 합니다 (Docker 네트워크 생성 필요).

```bash
cd deploy/monitor
cp .env.example .env
docker compose up -d
docker compose down
```

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `GRAFANA_PASSWORD` | `admin` | Grafana 관리자 비밀번호 |
| `APP_NETWORK` | `spring-ai-mcp-net` | 연결할 앱 네트워크 (stg: `spring-ai-mcp-stg-net` / prod: `spring-ai-mcp-prod-net`) |

**접속**

```
Grafana:    http://localhost:3000
Prometheus: http://localhost:9090
```

**Spring Boot 대시보드**
1. Dashboards → Import → ID `19004` → Load
2. Datasource: Prometheus → Import

**로그 조회**
1. Explore → Datasource: Loki
2. Label filter: `container = dev-app-1`

---

## 기타 명령어

```bash
# 이미지 재빌드
docker compose up -d --build

# 컨테이너 상태
docker compose ps

# 앱 쉘 접속
docker compose exec app sh

# PostgreSQL 접속
docker compose exec postgres psql -U ${DB_USERNAME} -d ${DB_NAME}

# 헬스체크
curl http://localhost:8080/actuator/health

# MCP Inspector
npx @modelcontextprotocol/inspector
# Transport: Streamable HTTP / URL: http://localhost:8080/mcp / Header: X-API-Key: <값>
```

## DB 초기화

볼륨 최초 생성 시 `init.sql`이 자동 실행됩니다. 수동 적용이 필요한 경우:

```bash
docker compose exec postgres psql -U ${DB_USERNAME} -d ${DB_NAME} \
  -f /docker-entrypoint-initdb.d/init.sql
```
