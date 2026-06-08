# Deploy Guide

## 구조

```
deploy/
├── Dockerfile
├── initdb/
│   └── init.sql          ← PostgreSQL 최초 기동 시 자동 실행 (sample_item 스키마)
├── dev/
│   ├── docker-compose.yml
│   ├── .env.example
│   └── .env              ← cp .env.example .env 후 수정
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

**요구사항:** Docker 24+, Docker Compose v2.4+

---

## 인증 방식 (JWT Bearer Token)

HMAC-SHA256으로 서명된 JWT를 `Authorization: Bearer <token>` 헤더로 전달합니다.  
토큰은 MCP 서버 외부에서 발급하며, 서버는 `JWT_SECRET`으로 서명 검증만 수행합니다.

**JWT 클레임 형식:**
```json
{
  "sub": "agent-name",
  "roles": ["mcp-user"],
  "iat": 1749123456,
  "exp": 1749127056
}
```

**시크릿키 생성:**
```bash
openssl rand -base64 32
```

---

## PostgreSQL 배포 방식

각 환경의 docker-compose는 **두 가지 모드**를 지원합니다.

### 모드 A — 내장 PostgreSQL (개발/테스트용)

`--profile db` 옵션으로 PostgreSQL 컨테이너를 함께 기동합니다.  
최초 기동 시 `initdb/init.sql`이 자동 실행되어 스키마를 생성합니다.

```bash
docker compose --profile db up -d --build
```

`DB_URL`을 내장 컨테이너 주소로 설정합니다:
```
DB_URL=jdbc:postgresql://postgres:5432/<DB_NAME>
```

### 모드 B — 외부 PostgreSQL (운영 권장)

`--profile db` 없이 앱만 기동합니다.  
`DB_URL`에 외부 PostgreSQL 주소를 지정합니다.

```bash
# .env에서 DB_URL을 외부 서버로 설정
DB_URL=jdbc:postgresql://db.example.com:5432/mydb

docker compose up -d --build
```

외부 DB에 스키마가 없을 경우 `initdb/init.sql`을 수동으로 적용합니다:
```bash
psql -h db.example.com -U <username> -d <dbname> -f deploy/initdb/init.sql
```

---

## dev

`ddl-auto: validate` · 포트 8090(기본)

```bash
cd deploy/dev
cp .env.example .env   # JWT_SECRET, DB_URL 등 설정

# 내장 DB 포함 기동
docker compose --profile db up -d --build

# 외부 DB 사용 시 (.env의 DB_URL을 외부 주소로 변경 후)
docker compose up -d --build

docker compose logs -f app
docker compose down
```

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `DB_URL` | `jdbc:postgresql://postgres:5432/sample_db` | DB 접속 URL |
| `DB_NAME` | `sample_db` | DB명 (내장 postgres 전용) |
| `DB_USERNAME` | `postgres` | DB 사용자 |
| `DB_PASSWORD` | `postgres` | DB 비밀번호 |
| `JWT_SECRET` | — | HMAC-SHA256 시크릿키 (Base64) |
| `TODO_API_URL` | `https://jsonplaceholder.typicode.com` | 외부 API URL |
| `PORT` | `8080` | 앱 포트 |

**포트 매핑:**

| 포트 | 서비스 |
|------|--------|
| `8090` | MCP 앱 (`POST /mcp`) |
| `5432` | PostgreSQL (--profile db 사용 시) |

---

## stg

`ddl-auto: validate` · 모든 환경변수 필수 · 네트워크: `spring-ai-mcp-stg-net`

```bash
cd deploy/stg
cp .env.example .env && vi .env   # 빈 값 없이 채울 것

# 내장 DB 포함
docker compose --profile db up -d --build

# 외부 DB 사용 시
docker compose up -d --build

docker compose down       # 볼륨 유지
docker compose down -v    # 볼륨 삭제
```

| 변수 | 설명 |
|------|------|
| `DB_URL` | DB 접속 URL |
| `DB_NAME` | DB명 (내장 postgres 전용) |
| `DB_USERNAME` | DB 사용자 |
| `DB_PASSWORD` | DB 비밀번호 |
| `JWT_SECRET` | HMAC-SHA256 시크릿키 (Base64) |
| `TODO_API_URL` | 외부 API URL |
| `PORT` | 앱 포트 (기본값: `8080`) |

---

## prod

`ddl-auto: none` · 모든 환경변수 필수 · 네트워크: `spring-ai-mcp-prod-net`

```bash
cd deploy/prod
cp .env.example .env && vi .env

# 내장 DB 포함
docker compose --profile db up -d --build

# 외부 DB 사용 시
docker compose up -d --build

docker compose down
docker compose down -v
```

| 변수 | 설명 |
|------|------|
| `DB_URL` | DB 접속 URL |
| `DB_NAME` | DB명 (내장 postgres 전용) |
| `DB_USERNAME` | DB 사용자 |
| `DB_PASSWORD` | DB 비밀번호 |
| `JWT_SECRET` | HMAC-SHA256 시크릿키 (Base64) |
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

---

## MCP Inspector 연결

```bash
npx @modelcontextprotocol/inspector
# Transport: Streamable HTTP
# URL: http://localhost:8080/mcp
# Header: Authorization: Bearer <JWT>
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

# 내장 PostgreSQL 접속 (--profile db 사용 시)
docker compose --profile db exec postgres psql -U ${DB_USERNAME} -d ${DB_NAME}

# 헬스체크 (내부 actuator 포트)
docker compose exec app wget -qO- http://localhost:8081/actuator/health

# 앱 로그
docker compose logs -f app
```

## DB 스키마 초기화

`initdb/init.sql`은 내장 PostgreSQL 최초 기동 시 자동 실행됩니다.  
외부 DB 또는 수동 적용이 필요한 경우:

```bash
psql -h <host> -U <username> -d <dbname> -f deploy/initdb/init.sql
```
