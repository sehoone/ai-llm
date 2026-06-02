# Deploy Guide

## 구조

```
deploy/
├── Dockerfile
├── initdb/
│   └── init.sql          ← PostgreSQL 최초 기동 시 자동 실행 (sample_item 스키마)
├── keycloak/
│   └── realm-export.json ← Keycloak Realm 자동 import 설정
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
│   └── ...
└── README.md
```

**요구사항:** Docker 24+, Docker Compose v2+

---

## 인증 방식 (Keycloak JWT)

이 서버는 **OAuth2 JWT Bearer Token** 인증을 사용합니다. 클라이언트는 Keycloak에서 발급받은 JWT를 `Authorization: Bearer <token>` 헤더로 전달해야 합니다.

```bash
# 토큰 발급 (Client Credentials Flow)
curl -s -X POST http://localhost:9191/realms/mcp/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=mcp-client&client_secret=dev-secret-change-me&grant_type=client_credentials" \
  | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4
```

| Keycloak Client | 용도 |
|---|---|
| `spring-ai-mcp` | Resource Server (토큰 검증 전용) |
| `mcp-client` | MCP 호출 클라이언트 (Client Credentials 발급) |

**dev 기본 secret**: `dev-secret-change-me` (realm-export.json에 정의)

---

## dev

`ddl-auto: validate` · PostgreSQL + Keycloak 포함 · 최초 기동 시 `initdb/init.sql` 자동 실행

```bash
cd deploy/dev
cp .env.example .env
docker compose up -d --build
docker compose logs -f app
docker compose down
```

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `DB_NAME` | `sample_db` | DB명 |
| `DB_USERNAME` | `postgres` | DB 사용자 |
| `DB_PASSWORD` | `postgres` | DB 비밀번호 |
| `KEYCLOAK_ADMIN` | `admin` | Keycloak 관리자 ID |
| `KEYCLOAK_ADMIN_PASSWORD` | `admin` | Keycloak 관리자 비밀번호 |
| `KEYCLOAK_CLIENT_ID` | `mcp-client` | MCP 클라이언트 ID |
| `TODO_API_URL` | `https://jsonplaceholder.typicode.com` | 외부 API URL |
| `PORT` | `8080` | 앱 포트 |

**포트 매핑:**

| 포트 | 서비스 |
|------|------|
| `8080` | MCP 앱 (`POST /mcp`) |
| `9191` | Keycloak 관리 콘솔 (http://localhost:9191) |
| `5432` | PostgreSQL |

---

## stg

`ddl-auto: validate` · 모든 환경변수 필수 · 네트워크: `spring-ai-mcp-stg-net`

```bash
cd deploy/stg
cp .env.example .env && vi .env   # 빈 값 없이 채울 것
docker compose up -d --build
docker compose down               # 볼륨 유지
docker compose down -v            # 볼륨 삭제
```

| 변수 | 설명 |
|------|------|
| `DB_NAME` | DB명 |
| `DB_USERNAME` | DB 사용자 |
| `DB_PASSWORD` | DB 비밀번호 |
| `KEYCLOAK_ISSUER_URI` | Keycloak Realm URL (예: `https://keycloak.example.com/realms/mcp`) |
| `KEYCLOAK_CLIENT_ID` | MCP 클라이언트 ID (기본: `mcp-client`) |
| `TODO_API_URL` | 외부 API URL |
| `PORT` | 앱 포트 (기본값: `8080`) |

---

## prod

`ddl-auto: none` · 모든 환경변수 필수

```bash
cd deploy/prod
cp .env.example .env && vi .env   # 빈 값 없이 채울 것
docker compose up -d --build
docker compose down               # 볼륨 유지
docker compose down -v            # 볼륨 삭제
```

| 변수 | 설명 |
|------|------|
| `DB_NAME` | DB명 |
| `DB_USERNAME` | DB 사용자 |
| `DB_PASSWORD` | DB 비밀번호 |
| `KEYCLOAK_ISSUER_URI` | Keycloak Realm URL |
| `KEYCLOAK_CLIENT_ID` | MCP 클라이언트 ID |
| `TODO_API_URL` | 외부 API URL |
| `PORT` | 앱 포트 (기본값: `8080`) |

---

## monitor

Prometheus + Grafana + Loki + Promtail

**선행 조건:** dev 또는 prod가 먼저 실행 중이어야 합니다 (Docker 네트워크 생성 필요).

> Prometheus는 포트 9090 사용. dev Keycloak은 포트 9191 사용 (충돌 없음).

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
Keycloak:   http://localhost:9191 (dev 환경)
```

**Spring Boot 대시보드**
1. Dashboards → Import → ID `19004` → Load
2. Datasource: Prometheus → Import

---

## MCP Inspector 연결

```bash
# 1. 토큰 발급
TOKEN=$(curl -s -X POST http://localhost:9191/realms/mcp/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=mcp-client&client_secret=dev-secret-change-me&grant_type=client_credentials" \
  | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

# 2. MCP Inspector 실행
npx @modelcontextprotocol/inspector
# Transport: Streamable HTTP
# URL: http://localhost:8080/mcp
# Header: Authorization: Bearer <위 토큰>
```

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

# 앱 로그
docker compose logs -f app
```

## DB 초기화

`deploy/initdb/init.sql`이 PostgreSQL 볼륨 최초 생성 시 자동 실행됩니다. 수동 적용이 필요한 경우:

```bash
docker compose exec postgres psql -U ${DB_USERNAME} -d ${DB_NAME} \
  -f /docker-entrypoint-initdb.d/init.sql
```
