# Deploy Guide — mcp-platform

전체 스택(nginx · admin · platform · mcp · PostgreSQL)을 Docker Compose로 단일 서버에 배포하는 가이드입니다.

**요구사항:** Docker 24+, Docker Compose v2.4+, openssl

---

## 디렉토리 구조

```
deploy/
├── README.md
├── docker-compose.yml      ← 앱 스택 (db · nginx · platform · mcp · admin)
├── .env.example            ← 환경변수 템플릿
├── .env                    ← 실제 환경변수 (git 제외)
├── deploy.sh               ← 배포 헬퍼 (Linux/macOS)
├── initdb/
│   └── init.sh             ← PostgreSQL 최초 기동 시 DB·테이블 자동 생성
├── nginx/
│   └── nginx.conf          ← Nginx 리버스 프록시 설정
└── monitor/
    ├── docker-compose.yml  ← 모니터링 스택 (Prometheus · Loki · Grafana)
    ├── .env.example
    ├── prometheus/
    │   ├── prometheus.yml
    │   └── rules/alerts.yml
    ├── loki/loki-config.yml
    ├── promtail/promtail-config.yml
    └── grafana/provisioning/
        ├── datasources/
        ├── dashboards/     ← MCP Platform Overview 대시보드 포함
        └── alerting/
```

---

## 서비스 구성

### 앱 스택 (`docker-compose.yml`)

| 서비스 | 컨테이너 | 외부 포트 | 역할 |
|--------|---------|----------|------|
| `db` | mcp-platform-db | — | PostgreSQL (llm_db + sample_db) |
| `nginx` | mcp-platform-nginx | **80** | 리버스 프록시 (단일 진입점) |
| `platform` | mcp-platform-platform | 8080 (직접 접근용) | 인증 · 사용자 · API 키 관리 |
| `mcp` | mcp-platform-mcp | 8081 (직접 접근용) | MCP 서버 (Streamable HTTP) |
| `admin` | mcp-platform-admin | 3000 (직접 접근용) | Next.js 관리 UI |

### 포트 정리

| 포트 | 방향 | 설명 |
|------|------|------|
| `80` | 외부 → nginx | **메인 진입점** |
| `8080` | 외부 → platform | 직접 접근용 (디버깅) |
| `8081` | 외부 → mcp | 직접 접근용 (디버깅) |
| `3000` | 외부 → admin | 직접 접근용 (디버깅) |
| `platform:8081` | 내부 전용 | platform Actuator / Prometheus |
| `mcp:8081` | 내부 전용 | mcp Actuator / Prometheus |

> **주의:** 호스트의 `localhost:8081`은 mcp 앱 포트(`8081:8080` 매핑)입니다.  
> 모니터링 스택이 scrape하는 `mcp:8081`은 Docker 내부 네트워크 경유 관리 포트(Actuator)입니다.

### Nginx 라우팅

`nginx/nginx.conf`가 포트 80으로 들어오는 모든 요청을 서비스별로 분기합니다.

| 경로 | 대상 | 비고 |
|------|------|------|
| `GET /api/health` | admin `:3000` | exact match — Next.js 헬스 전용 |
| `/api/*` | platform `:8080` | REST API, read_timeout 60s |
| `/swagger-ui/*` | platform `:8080` | Swagger UI |
| `/v3/*` | platform `:8080` | OpenAPI spec |
| `/mcp` | mcp `:8080` | Streamable HTTP + SSE (buffering off, timeout 1h) |
| `/` (그 외) | admin `:3000` | Next.js catch-all |

**네트워크:** `mcp-platform-net`  
**볼륨:** `mcp-platform-db` (PostgreSQL 데이터)

**기동 순서 (자동 보장):**
```
db (healthy) → platform (healthy) → mcp, admin → nginx
```

---

## 최초 배포

### 1. 환경변수 설정

```bash
cd deploy
cp .env.example .env
```

**필수 변경 항목:**

| 변수 | 예시 | 설명 |
|------|------|------|
| `DB_PASSWORD` | `aSt0ngP@ssw0rd` | PostgreSQL 비밀번호 |
| `JWT_SECRET_KEY` | `$(openssl rand -hex 32)` | JWT 서명 키 (32자 이상) |
| `NEXT_PUBLIC_API_URL` | `http://192.168.1.100` | **브라우저에서** Nginx에 접근하는 주소 |

> `NEXT_PUBLIC_API_URL`은 빌드 시 JS 번들에 포함됩니다.  
> Nginx를 경유하므로 포트 없이 서버 IP 또는 도메인만 입력합니다.  
> `localhost`는 서버 배포 시 사용 불가 — 브라우저가 실행되는 클라이언트 PC를 가리킵니다.

### 2. 빌드 & 기동

**Linux / macOS (권장):**

```bash
chmod +x deploy.sh
./deploy.sh up -d --build
```

`deploy.sh`는 `.env`의 `NEXT_PUBLIC_API_URL`을 `admin-front/.env.production`에 자동 기록 후 `docker compose`를 실행합니다.

**Windows PowerShell:**

```powershell
# admin-front 빌드 환경변수 설정 (포트 없이 서버 IP만)
Set-Content ../admin-front/.env.production "NEXT_PUBLIC_API_URL=http://192.168.1.100"

# 빌드 & 기동
docker compose up -d --build
```

기동 완료 확인:

```bash
docker compose ps
# 5개 컨테이너 모두 STATUS: Up (healthy 또는 Up) 이어야 합니다
# nginx는 healthcheck 없이 Up 상태
```

### 3. 초기 관리자 계정 생성

```bash
# 회원가입 (최초 계정은 USER 역할)
curl -X POST http://localhost/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","email":"admin@example.com","password":"Admin1234!"}'

# DB에서 ADMIN 역할로 변경
docker compose exec db psql -U postgres -d llm_db \
  -c "UPDATE llmonl.users SET role='ADMIN' WHERE email='admin@example.com';"
```

이후 `http://localhost`에서 로그인합니다.

### 4. MCP 클라이언트용 API 키 발급

admin-front 로그인 후 **Configuration → API Keys → 생성** 또는 API로 직접:

```bash
# 로그인 (응답에서 accessToken 추출)
TOKEN=$(curl -s -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"Admin1234!"}' \
  | grep -o '"accessToken":"[^"]*"' | cut -d'"' -f4)

# API 키 생성
curl -X POST http://localhost/api/v1/api-keys \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"my-mcp-client"}'
```

응답의 `key` 값(`sk-...`)을 MCP 클라이언트 설정에 사용합니다.

---

## MCP 클라이언트 연결

mcp 서비스는 **Streamable HTTP** transport로 `POST /mcp` 엔드포인트를 노출합니다.  
모든 요청에 `Authorization: Bearer sk-...` 헤더가 필요합니다.

### MCP Inspector (테스트용)

```bash
npx @modelcontextprotocol/inspector
# Transport: Streamable HTTP
# URL:       http://YOUR_SERVER_IP/mcp        ← Nginx 경유 (권장)
# URL:       http://YOUR_SERVER_IP:8081/mcp   ← 직접 접근
# Header:    Authorization: Bearer sk-your-api-key
```

### Claude Desktop

`%APPDATA%\Claude\claude_desktop_config.json` (Windows) /  
`~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "mcp-platform": {
      "url": "http://YOUR_SERVER_IP/mcp",
      "headers": {
        "Authorization": "Bearer sk-your-api-key-here"
      }
    }
  }
}
```

### 직접 HTTP 호출

```bash
# 1. 세션 초기화 (Session ID 획득)
SESSION_RESP=$(curl -si -X POST http://localhost/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer sk-your-api-key" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}')

SESSION_ID=$(echo "$SESSION_RESP" | grep -i "mcp-session-id" | tr -d '\r' | awk '{print $2}')

# 2. Tool 목록 조회
curl -s -X POST http://localhost/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer sk-your-api-key" \
  -H "Mcp-Session-Id: $SESSION_ID" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'

# 3. 세션 종료
curl -s -X DELETE http://localhost/mcp \
  -H "Authorization: Bearer sk-your-api-key" \
  -H "Mcp-Session-Id: $SESSION_ID"
```

---

## 모니터링 스택

앱 스택이 기동 중인 상태에서 별도로 실행합니다 (`mcp-platform-net` 네트워크 필요).

### 기동

```bash
cd deploy/monitor
cp .env.example .env   # GRAFANA_PASSWORD 필수 설정
docker compose up -d
```

### 접속

| 서비스 | 주소 | 설명 |
|--------|------|------|
| Grafana | `http://localhost:3001` | 대시보드 · 알림 |
| Prometheus | `http://localhost:9090` | 메트릭 · 쿼리 |

### 구성 요소

| 컨테이너 | 역할 |
|---------|------|
| Prometheus | platform · mcp Actuator 메트릭 15초 주기 수집, 15일 보관 |
| Loki | 컨테이너 로그 수집, 30일 보관 |
| Promtail | Docker 소켓 감시 → mcp-platform 컨테이너 로그 자동 수집 |
| Grafana | 시각화 + Unified Alerting |

### Scrape 대상

| 대상 | 주소 (내부) | 메트릭 경로 |
|------|------------|------------|
| platform-server | `platform:8081` | `/actuator/prometheus` |
| spring-ai-mcp | `mcp:8081` | `/actuator/prometheus` |

### Grafana 첫 설정

1. `http://localhost:3001` 접속 → admin / `.env`의 `GRAFANA_PASSWORD`
2. **Dashboards → MCP Platform → MCP Platform Overview** 자동 프로비저닝 확인
3. Spring Boot JVM 대시보드 추가: Dashboards → Import → ID `19004` → Datasource: Prometheus

### 알림 설정

```bash
# monitor/.env 에서 SMTP 설정 후 grafana 재기동
SMTP_ENABLED=true
SMTP_HOST=smtp.gmail.com:587
SMTP_USER=your@gmail.com
SMTP_PASSWORD=app-password
SMTP_FROM=alert@example.com
```

이후 Grafana UI: **Alerting → Contact points → default-email** 에서 수신 이메일 등록.

**알림 규칙 (자동 프로비저닝):**

| 규칙 | 조건 | 심각도 |
|------|------|--------|
| ServiceDown | scrape 실패 1분 | critical |
| JvmHeapMemoryHigh | 힙 사용률 > 80% (5분) | warning |
| JvmHeapMemoryCritical | 힙 사용률 > 95% (2분) | critical |
| HttpHighErrorRate | 5xx 비율 > 5% (5분) | warning |
| HttpSlowResponse | p99 > 3초 (5분) | warning |
| McpAuthFailureHigh | 401 > 10/분 (3분) | warning |

### 모니터링 중지

```bash
cd deploy/monitor
docker compose down       # 데이터 유지
docker compose down -v    # 데이터 포함 삭제
```

---

## 일상 운영

```bash
# 전체 로그 스트리밍
docker compose logs -f

# 서비스별 로그
docker compose logs -f nginx
docker compose logs -f platform
docker compose logs -f mcp
docker compose logs -f admin

# 컨테이너 상태 및 헬스 확인
docker compose ps

# 특정 서비스 재시작
docker compose restart nginx
docker compose restart mcp

# 중지 (데이터 유지)
docker compose down

# 중지 + 볼륨 삭제 (데이터 완전 삭제)
docker compose down -v
```

---

## 이미지 업데이트 (재배포)

```bash
# 특정 서비스만 재빌드
docker compose up -d --build platform
docker compose up -d --build mcp

# admin 재빌드 (NEXT_PUBLIC_API_URL 변경 시 반드시 재빌드)
./deploy.sh up -d --build admin

# 전체 재빌드
./deploy.sh up -d --build

# Nginx 설정만 변경한 경우 — 재빌드 없이 reload
docker compose restart nginx
```

---

## 환경변수 전체 목록

### 앱 스택 (`.env`)

| 변수 | 기본값 | 필수 | 설명 |
|------|--------|:----:|------|
| `DB_USERNAME` | `postgres` | | PostgreSQL 사용자 |
| `DB_PASSWORD` | — | ✅ | PostgreSQL 비밀번호 |
| `PLATFORM_DB` | `llm_db` | | platform DB명 |
| `MCP_DB` | `sample_db` | | mcp DB명 |
| `JWT_SECRET_KEY` | — | ✅ | JWT 서명 시크릿키 (32자 이상) |
| `JWT_ACCESS_MINUTES` | `10` | | access 토큰 만료 (분) |
| `JWT_REFRESH_MINUTES` | `10080` | | refresh 토큰 만료 (분, 7일) |
| `NGINX_PORT` | `80` | | Nginx 외부 노출 포트 (단일 진입점) |
| `PLATFORM_PORT` | `8080` | | platform 직접 접근 포트 (디버깅용) |
| `MCP_PORT` | `8081` | | mcp 직접 접근 포트 (디버깅용) |
| `ADMIN_PORT` | `3000` | | admin 직접 접근 포트 (디버깅용) |
| `TODO_API_URL` | `https://jsonplaceholder.typicode.com` | | SampleTool 외부 API |
| `NEXT_PUBLIC_API_URL` | — | ✅ | 브라우저→Nginx 주소 (빌드 시 번들 포함, 포트 불필요) |

### 모니터링 스택 (`monitor/.env`)

| 변수 | 기본값 | 필수 | 설명 |
|------|--------|:----:|------|
| `APP_NETWORK` | `mcp-platform-net` | | 앱 스택 네트워크명 |
| `GRAFANA_PASSWORD` | — | ✅ | Grafana 관리자 비밀번호 |
| `GRAFANA_PORT` | `3001` | | Grafana 외부 포트 |
| `PROMETHEUS_PORT` | `9090` | | Prometheus 외부 포트 |
| `GRAFANA_DOMAIN` | `localhost` | | 리버스 프록시 사용 시 도메인 |
| `SMTP_ENABLED` | `false` | | 이메일 알림 활성화 |
| `SMTP_HOST` | — | | SMTP 서버 (예: smtp.gmail.com:587) |
| `SMTP_USER` | — | | SMTP 사용자 |
| `SMTP_PASSWORD` | — | | SMTP 비밀번호 |
| `SMTP_FROM` | — | | 발신 이메일 |

---

## 헬스체크

```bash
# Nginx (포트 80)
curl -o /dev/null -w "%{http_code}" http://localhost/api/health
# 200 이면 정상

# platform REST API (Nginx 경유) — POST 전용 엔드포인트에 GET → 403 Forbidden
curl -o /dev/null -w "%{http_code}" http://localhost/api/v1/auth/login
# 403 → platform 도달 확인 (Spring Security가 GET 차단)

# platform Actuator (컨테이너 내부 관리 포트)
docker compose exec platform curl -s http://localhost:8081/actuator/health

# platform Prometheus 메트릭 (컨테이너 내부)
docker compose exec platform curl -s http://localhost:8081/actuator/prometheus | head -10

# mcp Actuator (컨테이너 내부 관리 포트)
docker compose exec mcp curl -s http://localhost:8081/actuator/health

# admin Next.js 헬스
curl http://localhost/api/health
```

---

## PostgreSQL 직접 접속

```bash
# platform DB (llmonl 스키마)
docker compose exec db psql -U postgres -d llm_db

# mcp DB
docker compose exec db psql -U postgres -d sample_db

# 활성 API 키 목록
docker compose exec db psql -U postgres -d llm_db -c \
  "SELECT u.username, k.name, left(k.key,12)||'...' AS key, k.is_active, k.expires_at
   FROM llmonl.api_key k JOIN llmonl.users u ON u.id = k.user_id
   WHERE k.is_active = true ORDER BY k.created_at DESC;"

# 사용자 역할 변경
docker compose exec db psql -U postgres -d llm_db -c \
  "UPDATE llmonl.users SET role='ADMIN' WHERE email='user@example.com';"
```

---

## DB 스키마 재초기화

> ⚠️ 기존 데이터가 모두 삭제됩니다.

```bash
docker compose down -v        # 볼륨까지 삭제
./deploy.sh up -d --build     # 재빌드 & 기동 (init.sh 재실행)
```

`down`만 하면 볼륨이 유지되어 init.sh가 재실행되지 않습니다.

---

## mcp 단독 배포

MCP 서버만 별도로 배포하려면 `spring-ai-mcp/deploy/`의 환경별 compose를 사용합니다.  
`PLATFORM_URL` 환경변수에 이미 운영 중인 platform-server 주소를 지정해야 합니다.

자세한 내용: [`spring-ai-mcp/deploy/README.md`](../spring-ai-mcp/deploy/README.md)
