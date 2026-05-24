# FastMCP Base

[FastMCP](https://gofastmcp.com) 기반의 멀티 도메인 MCP 서버 프로젝트.  
`python main.py server` 한 명령으로 날씨·뉴스·데이터베이스·유틸리티 **19개 도구**를 한 번에 노출합니다.

---

## 요구사항

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) 패키지 매니저
- FastMCP 3.3.1+
- PostgreSQL (DB 도구 사용 시)
- OpenWeatherMap API 키 (실제 날씨 데이터 사용 시)
- NewsAPI 키 (실제 뉴스 데이터 사용 시)

> API 키 없이도 `demo_key` 유지 시 샘플 데이터로 동작합니다.

---

## 빠른 시작

**Linux / macOS**
```bash
# 1. 의존성 설치
uv sync

# 2. 환경변수 설정 — deploy/.env.example 참고
cp deploy/.env.example .env.local

# 3. DB 초기화 (최초 1회)
psql -U postgres -d fastmcp_db -f scripts/schema.sql

# 4. 서버 실행
APP_ENV=local uv run python main.py server
```

**Windows (PowerShell)**
```powershell
# 1. 의존성 설치
uv sync

# 2. 환경변수 설정 — deploy/.env.example 참고
Copy-Item deploy\.env.example .env.local

# 3. DB 초기화 (최초 1회)
psql -U postgres -d fastmcp_db -f scripts/schema.sql

# 4. 서버 실행
$env:APP_ENV="local"; uv run python main.py server
```

서버가 `http://0.0.0.0:8000/mcp` 에서 대기합니다.

---

## 환경변수 설정

`APP_ENV` 값에 따라 해당 `.env.{APP_ENV}` 파일을 자동으로 로드합니다.

| APP_ENV | 파일 | 용도 |
|---------|------|------|
| `local` (기본값) | `.env.local` | 로컬 개발 — demo API, DEBUG 로그 |
| `dev` | `.env.dev` | 개발 서버 — 실제 API, INFO 로그 |
| `prod` | `.env.prod` | 프로덕션 — 실제 API, WARNING 로그 |

### 초기 설정

**Linux / macOS**
```bash
cp deploy/.env.example .env.local
cp deploy/.env.example .env.dev
cp deploy/.env.example .env.prod
```

**Windows (PowerShell)**
```powershell
Copy-Item deploy\.env.example .env.local
Copy-Item deploy\.env.example .env.dev
Copy-Item deploy\.env.example .env.prod
```

### 주요 환경변수

```ini
# 외부 API (없으면 demo_key 유지 — 샘플 데이터 반환)
OPENWEATHER_API_KEY=demo_key
NEWS_API_KEY=demo_key

# PostgreSQL 연결
DATABASE_URL=postgresql://user:password@host:5432/fastmcp_db

# JWT 인증
# 프로덕션: openssl rand -hex 32 으로 반드시 교체
JWT_SECRET_KEY=your-secret-key
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30   # 액세스 토큰 유효 시간 (분, 기본 30)
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7      # 리프레시 토큰 유효 시간 (일, 기본 7)

# 인증 사용자 — "username:password,user2:pass2" 형식 (bcrypt 해시도 지원)
# 해시 생성: python -c "import bcrypt; print(bcrypt.hashpw(b'pw', bcrypt.gensalt()).decode())"
AUTH_USERS=admin:admin123
AUTH_MODE=global   # global(미들웨어 전체 차단) | per-tool(@protected 도구가 직접 검증)

# 서버
MCP_TRANSPORT=streamable-http   # stdio | streamable-http | sse
MCP_HOST=0.0.0.0
MCP_PORT=8000
MCP_WORKERS=1                   # workers > 1 시 다중 프로세스 (CPU 바운드에 유리)

# HTTP 클라이언트
HTTP_TIMEOUT=10.0        # 외부 API 타임아웃 (초)
HTTP_MAX_RETRIES=3       # 5xx / 연결 오류 재시도 횟수

# 데이터베이스 페이지네이션
DB_MAX_PAGE_SIZE=100     # 목록 조회 최대 페이지 크기
CONTENT_PREVIEW_LENGTH=200   # 게시글 목록에서 본문 미리보기 길이

# 로깅
LOG_LEVEL=INFO   # DEBUG | INFO | WARNING | ERROR
                 # DEBUG 설정 시 uvicorn access log 자동 활성화

# HTTPS (nginx 사용 시)
DOMAIN=your-domain.com
NGINX_MODE=https   # https(기본, SSL 필요) | http(SSL 없이 HTTP 전용)
```

---

## 서버 실행

**Linux / macOS**
```bash
APP_ENV=local uv run python main.py server   # 로컬 개발
APP_ENV=dev   uv run python main.py server   # 개발 서버
APP_ENV=prod  uv run python main.py server   # 프로덕션
```

**Windows (PowerShell)**
```powershell
$env:APP_ENV="local"; uv run python main.py server   # 로컬 개발
$env:APP_ENV="dev";   uv run python main.py server   # 개발 서버
$env:APP_ENV="prod";  uv run python main.py server   # 프로덕션
```

`MCP_TRANSPORT` 값에 따라 서버 모드가 달라집니다.

| 값 | 동작 |
|----|------|
| `streamable-http` (기본) | uvicorn HTTP 서버, JWT 인증 포함 |
| `sse` | uvicorn HTTP 서버 (SSE 전용, JWT 인증 포함) |
| `stdio` | 표준 입출력 모드, Claude Desktop 직접 연결용 (JWT 불필요) |

---

## HTTP 엔드포인트

| 경로 | 메서드 | 인증 | 설명 |
|------|--------|------|------|
| `/mcp` | GET / POST | Bearer | MCP 프로토콜 엔드포인트 |
| `/health` | GET | 없음 | 헬스체크 (DB 상태 포함) |
| `/auth/token` | POST | 없음 | 액세스·리프레시 토큰 발급 (5회/분 제한) |
| `/auth/refresh` | POST | 없음 | 액세스 토큰 갱신 |
| `/metrics` | GET | 없음 | Prometheus 메트릭 (내부망 전용 권장) |

---

## 인증

HTTP transport 사용 시 모든 MCP 요청에 JWT Bearer 토큰이 필요합니다.

```bash
# 토큰 발급
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your_password"}'

# 응답
# {"access_token": "eyJ...", "refresh_token": "eyJ...", "token_type": "bearer", "expires_in": 1800}
```

FastMCP Client 사용 시:

```python
from fastmcp import Client

async with Client("http://localhost:8000/mcp", auth="<access_token>") as client:
    tools = await client.list_tools()
```

토큰 갱신:

```bash
curl -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJ..."}'
```

---

## MCP 도구 목록 (19개)

### 날씨

| 도구 | 파라미터 | 설명 |
|------|----------|------|
| `get_weather` | `city`, `country_code?` | 현재 날씨 조회 |
| `get_forecast` | `city`, `country_code?`, `days?=5` | 날씨 예보 (최대 5일) |

### 뉴스

| 도구 | 파라미터 | 설명 |
|------|----------|------|
| `get_top_headlines` | `country?=kr`, `category?`, `page_size?=10` | 헤드라인 뉴스 |
| `search_news` | `query`, `language?=ko`, `sort_by?`, `page_size?=10` | 키워드 검색 |
| `get_news_sources` | `category?`, `language?=ko`, `country?=kr` | 뉴스 소스 목록 |

### 데이터베이스

| 도구 | 파라미터 | 설명 |
|------|----------|------|
| `create_user` | `username`, `email`, `full_name?` | 사용자 생성 |
| `get_users` | `limit?=10`, `offset?=0` | 사용자 목록 |
| `get_user_by_id` | `user_id` | 사용자 상세 (게시글 포함) |
| `create_post` | `title`, `content`, `author_id`, `is_published?=false` | 게시글 생성 |
| `get_posts` | `limit?=10`, `offset?=0`, `published_only?=false` | 게시글 목록 |
| `update_post` | `post_id`, `title?`, `content?`, `is_published?` | 게시글 수정 |
| `delete_post` | `post_id` | 게시글 삭제 |
| `search_posts` | `query`, `limit?=10` | 게시글 검색 |
| `get_database_stats` | — | 통계 + 최근 활동 |
| `execute_raw_query` | `query`, `params?` | SELECT 전용 쿼리 (쓰기 차단) |
| `get_table_schema` | `table_name` | 테이블 컬럼 구조 조회 |

### 유틸리티

| 도구 | 파라미터 | 설명 |
|------|----------|------|
| `get_time` | — | 현재 UTC 시간 + 요일 |
| `calculate` | `expression` | 수식 계산 (AST 기반, eval 미사용) |
| `ping_server` | `url` | 서버 응답 시간 측정 |

---

## Docker 배포

### 개발 환경

```bash
cd deploy
cp .env.example .env
# .env 에서 POSTGRES_PASSWORD, JWT_SECRET_KEY, AUTH_USERS 변경
docker compose up -d
```

SSL 없이 HTTP만 사용하려면 `.env`에 `NGINX_MODE=http` 를 추가하고 nginx 프로파일로 실행합니다.

```bash
docker compose --profile nginx up -d
```

### 프로덕션 (HTTPS 포함)

```bash
# 1. SSL 인증서 준비 (Let's Encrypt 예시)
certbot certonly --standalone -d your-domain.com
mkdir -p deploy/ssl
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem deploy/ssl/cert.pem
cp /etc/letsencrypt/live/your-domain.com/privkey.pem   deploy/ssl/key.pem

# 2. .env 에서 DOMAIN=your-domain.com 설정

# 3. 프로덕션 설정 오버라이드 + nginx 포함하여 실행
cd deploy
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

프로덕션 컴포즈에서 적용되는 설정:
- `mcp` 컨테이너의 직접 포트 노출 제거 (nginx가 80/443 처리)
- nginx 서비스 기본 활성화
- 리소스 제한 (mcp: CPU 1, MEM 512M / postgres: MEM 1G)
- 로그 로테이션 (10MB × 5개)

### Prometheus + Grafana 모니터링

```bash
# 모니터링 스택 함께 실행
docker compose --profile monitoring up -d

# Grafana: http://localhost:3000  (기본 admin / admin)
# Prometheus scrape 설정에서 mcp:8000/metrics 를 타겟으로 추가
```

---

## 아키텍처

```
src/
├── core/
│   ├── config.py       # APP_ENV 기반 환경변수 관리 (pydantic-settings)
│   ├── logging.py      # JSON 구조화 로그 + request_id 자동 포함 + tool_logger 데코레이터
│   ├── auth.py         # JWT 토큰 생성·검증·미들웨어 (bcrypt 비밀번호 지원)
│   ├── db.py           # async SQLAlchemy 엔진·세션 팩토리
│   ├── http.py         # httpx AsyncClient + 지수 백오프 재시도
│   ├── context.py      # request_id ContextVar (로그 correlation 용)
│   └── middleware.py   # RequestIDMiddleware (X-Request-ID 헤더)
├── auth/
│   └── setup.py        # /health, /auth/token, /auth/refresh 라우트 + slowapi rate limit
├── weather/            # 날씨 도메인 (2 tools, 2 resources, 2 prompts)
├── news/               # 뉴스 도메인 (3 tools, 2 resources, 2 prompts)
├── users/              # 사용자/게시글 도메인 (11 tools, 2 resources, 1 prompt)
└── utils/              # 유틸리티 도메인 (3 tools)

src/app.py              # 도메인 모듈 import → 도구 등록 트리거
src/asgi.py             # ASGI 진입점 — 미들웨어 조합 후 app 빌드 (uvicorn이 import)
main.py                 # CLI 진입점

deploy/
├── Dockerfile
├── docker-compose.yml          # 기본 스택 (postgres, mcp, pgadmin, loki, grafana)
├── docker-compose.prod.yml     # 프로덕션 오버라이드 (nginx 활성화, 포트 제한)
├── nginx.conf.template         # HTTPS 종단, /metrics 외부 차단
├── nginx-http.conf.template    # HTTP 전용 (NGINX_MODE=http 시 사용)
└── .env.example                # 환경변수 템플릿
```

### 주요 패턴

**단일 인스턴스**: `src/core/mcp.py`에 `mcp = FastMCP(...)` 하나. 모든 도메인이 동일 인스턴스에 등록

**Lifespan Context**: DB 엔진·HTTP 클라이언트를 lifespan에서 초기화 → `ctx.lifespan_context`로 도구에 주입

**JSON 구조화 로그**: 모든 로그 엔트리에 `ts`, `level`, `logger`, `msg`, `request_id` 포함

**비밀번호 보안**: `AUTH_USERS` 값에 bcrypt 해시 저장 가능 (`$2b$` 접두사 자동 감지)

**Rate Limiting**: `/auth/token`에 IP 기반 slowapi 제한 (기본 5회/분)

**Correlation ID**: 요청마다 UUID를 `X-Request-ID` 헤더로 발급, 모든 로그에 자동 포함

---

## Claude Desktop 연동

### stdio 모드 (로컬 직접 연결)

`.env.local`에서 `MCP_TRANSPORT=stdio` 로 변경 후 `claude_desktop_config.json`에 추가:

```json
{
  "mcpServers": {
    "fastmcp-base": {
      "command": "uv",
      "args": ["run", "python", "main.py", "server"],
      "cwd": "/path/to/fastmcp-base",
      "env": {"APP_ENV": "local"}
    }
  }
}
```

### streamable-http 모드 (서버 별도 기동)

```json
{
  "mcpServers": {
    "fastmcp-base": {
      "url": "http://localhost:8000/mcp",
      "headers": {"Authorization": "Bearer <access_token>"}
    }
  }
}
```

---

## 테스트

```bash
# 단위 테스트 (API 키 / DB 불필요)
uv run pytest tests/unit/ -v

# 통합 테스트 (PostgreSQL 필요)
uv run pytest tests/integration/ -v

# 전체
uv run pytest tests/
```

---

## 디버깅

### 1. DEBUG 로그 활성화

`.env.local`에서 `LOG_LEVEL=DEBUG` 로 변경하면 **uvicorn access log** + **도구 호출 상세 로그**가 함께 출력됩니다.

```bash
# Linux / macOS — 파일 수정 없이 즉시 확인
LOG_LEVEL=DEBUG APP_ENV=local uv run python main.py server
```
```powershell
# Windows (PowerShell)
$env:LOG_LEVEL="DEBUG"; $env:APP_ENV="local"; uv run python main.py server
```

로그는 JSON 구조로 출력됩니다 (`ts`, `level`, `logger`, `msg`, `request_id`, `tool`, `duration_ms`).

```json
{"ts":"2026-01-01T00:00:00+00:00","level":"INFO","logger":"weather.tools","msg":"tool_start","request_id":"abc-123","tool":"get_weather","city":"Seoul"}
{"ts":"2026-01-01T00:00:00.050+00:00","level":"INFO","logger":"weather.tools","msg":"tool_done","request_id":"abc-123","tool":"get_weather","city":"Seoul","status":"success","duration_ms":48.3}
```

### 2. MCP Inspector (브라우저 UI)

FastMCP 내장 Inspector로 도구를 브라우저에서 대화형으로 테스트합니다. 두 가지 방식이 있습니다.

---

**방식 A — stdio (간단, 토큰 불필요)**

Inspector가 Python 프로세스를 직접 관리합니다. 서버를 따로 띄울 필요 없습니다.

```bash
# Linux / macOS
MCP_TRANSPORT=stdio APP_ENV=local uv run fastmcp dev inspector src/app.py
```
```powershell
# Windows (PowerShell)
$env:APP_ENV="local"; $env:MCP_TRANSPORT="stdio"; uv run fastmcp dev inspector src/app.py
```

브라우저가 열리면 **Connect 버튼만 클릭**하면 됩니다.

---

**방식 B — StreamableHTTP (실서버 연동, 토큰 필요)**

터미널 두 개를 사용합니다.

터미널 1 — 서버 실행:
```bash
# Linux / macOS
APP_ENV=local uv run python main.py server
```
```powershell
# Windows (PowerShell)
$env:APP_ENV="local"; uv run python main.py server
```

터미널 2 — Inspector 실행:
```bash
# Linux / macOS
APP_ENV=local uv run fastmcp dev inspector src/app.py
```
```powershell
# Windows (PowerShell)
$env:APP_ENV="local"; uv run fastmcp dev inspector src/app.py
```

JWT 토큰 발급:
```bash
# Linux / macOS
curl -s -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```
```powershell
# Windows (PowerShell)
$body = '{"username":"admin","password":"admin123"}'
$token = (irm -Method Post http://localhost:8000/auth/token `
  -ContentType "application/json" -Body $body).access_token
echo $token
```

Inspector UI 연결 설정 — **Connect 전에 Headers를 먼저 입력해야 합니다:**

| 항목 | 값 |
|------|----|
| Transport | `StreamableHTTP` |
| URL | `http://localhost:8000/mcp` |
| Headers > Key | `Authorization` |
| Headers > Value | `Bearer <위에서 출력된 토큰값>` |

> Headers를 입력하지 않고 Connect하면 Inspector가 OAuth 자동 탐색을 시도하다 실패합니다. 반드시 토큰을 먼저 입력하세요.

토큰은 30분 후 만료됩니다. 만료 시 재발급하거나 `/auth/refresh`로 갱신하세요.

### 3. 헬스체크 및 엔드포인트 확인

```bash
# 서버 상태 + DB 연결 확인
curl http://localhost:8000/health

# 토큰 발급
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# 도구 목록 확인 (토큰 필요)
curl http://localhost:8000/mcp \
  -H "Authorization: Bearer <access_token>"
```

Windows PowerShell에서는 `curl` 대신 `Invoke-RestMethod`(irm) 사용:

```powershell
# 헬스체크
irm http://localhost:8000/health

# 토큰 발급
$body = '{"username": "admin", "password": "admin123"}'
$token = (irm -Method Post http://localhost:8000/auth/token `
  -ContentType "application/json" -Body $body).access_token

# 도구 목록 확인
irm http://localhost:8000/mcp -Headers @{Authorization="Bearer $token"}
```

### 4. 로드된 설정값 확인

실제로 어떤 `.env` 파일이 로드됐는지, 환경변수가 올바르게 적용됐는지 확인합니다.

```bash
# Linux / macOS
APP_ENV=local uv run python -c \
  "from src.core.config import get_settings; import json; print(json.dumps(get_settings().model_dump(), indent=2))"
```
```powershell
# Windows (PowerShell)
$env:APP_ENV="local"; uv run python -c `
  "from src.core.config import get_settings; import json; print(json.dumps(get_settings().model_dump(), indent=2))"
```

### 5. Python 클라이언트로 도구 직접 테스트

서버 없이 인메모리로 도구를 호출합니다. JWT 인증이 필요 없고 DB·API 키도 없이 `get_time`, `calculate` 같은 유틸 도구를 즉시 확인할 수 있습니다.

```bash
# Linux / macOS
APP_ENV=local uv run python -c "
import asyncio
from fastmcp import Client
from src.app import mcp

async def main():
    async with Client(mcp) as client:
        tools = await client.list_tools()
        print('등록된 도구:', [t.name for t in tools])
        result = await client.call_tool('get_time', {})
        print('get_time 결과:', result)

asyncio.run(main())
"
```

```powershell
# Windows (PowerShell)
$env:APP_ENV="local"; uv run python -c @'
import asyncio
from fastmcp import Client
from src.app import mcp

async def main():
    async with Client(mcp) as client:
        tools = await client.list_tools()
        print("등록된 도구:", [t.name for t in tools])
        result = await client.call_tool("get_time", {})
        print("get_time 결과:", result)

asyncio.run(main())
'@
```

> DB 도구(`create_user`, `get_posts` 등)는 `@protected` 데코레이터가 없는 경우 인메모리 테스트에서 호출 가능하지만, PostgreSQL 연결이 없으면 `ToolError`가 발생합니다. 에러 확인 시 `raise_on_error=False` 후 `result.is_error`로 검증하세요.

### 6. DB 연결 확인

```bash
# Linux / macOS
APP_ENV=local uv run python -c \
  "import asyncio; from src.core.db import test_connection; asyncio.run(test_connection())"
```
```powershell
# Windows (PowerShell)
$env:APP_ENV="local"; uv run python -c `
  "import asyncio; from src.core.db import test_connection; asyncio.run(test_connection())"
```

---

## 문제 해결

**API 키 없이 테스트** — `demo_key` 유지 시 날씨·뉴스 도구가 샘플 데이터를 반환합니다.

**DB 연결 오류** — `DATABASE_URL`이 올바른지 확인하고, PostgreSQL이 실행 중인지 점검합니다.

**401 Unauthorized** — `/auth/token`으로 토큰을 발급받아 `Authorization: Bearer <token>` 헤더를 추가합니다.

**429 Too Many Requests** — `/auth/token` 요청이 분당 5회를 초과했습니다. 잠시 후 다시 시도하세요.

**ping_server가 내부 URL을 거부함** — `ping_server` 도구는 SSRF 방어를 위해 `localhost`, 루프백 IP(`127.x.x.x`), 사설 IP(`192.168.x.x`, `10.x.x.x`), `.local` 호스트명을 차단합니다. 퍼블릭 URL만 사용 가능합니다.

**패키지 재설치**
```bash
# Linux / macOS
uv cache clean && uv sync --reinstall
```
```powershell
# Windows (PowerShell)
uv cache clean; uv sync --reinstall
```

**로그 상세 확인** — `.env.local`에서 `LOG_LEVEL=DEBUG` 설정 후 재실행합니다.
