# FastMCP Base

[FastMCP](https://gofastmcp.com) 기반의 멀티 도메인 MCP 서버 프로젝트.  
`python main.py server` 한 명령으로 날씨·뉴스·데이터베이스·유틸리티 **19개 도구**를 한 번에 노출합니다.

---

## 요구사항

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) 패키지 매니저
- PostgreSQL (DB 도구 사용 시)
- OpenWeatherMap API 키 (실제 날씨 데이터 사용 시)
- NewsAPI 키 (실제 뉴스 데이터 사용 시)

> API 키 없이도 `demo_key` 유지 시 샘플 데이터로 동작합니다.

---

## 빠른 시작

```bash
# 1. 의존성 설치
uv sync

# 2. 환경변수 설정 — deploy/.env.example 참고
cp deploy/.env.example .env.local

# 3. 서버 실행
APP_ENV=local uv run python main.py server
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

```bash
# 환경별 파일 생성 (최초 1회) — deploy/.env.example을 템플릿으로 사용
cp deploy/.env.example .env.local
cp deploy/.env.example .env.dev
cp deploy/.env.example .env.prod
```

각 파일에서 실제 값을 채웁니다.

### 주요 환경변수

```ini
# 외부 API (없으면 demo_key 유지)
OPENWEATHER_API_KEY=demo_key
NEWS_API_KEY=demo_key

# PostgreSQL 연결
DATABASE_URL=postgresql://user:password@host:5432/dbname

# JWT 인증 (프로덕션: openssl rand -hex 32 로 생성)
JWT_SECRET_KEY=your-secret-key
AUTH_USERS=admin:password

# 서버
MCP_TRANSPORT=streamable-http   # stdio | streamable-http
MCP_HOST=0.0.0.0
MCP_PORT=8000

# 로깅
LOG_LEVEL=INFO   # DEBUG | INFO | WARNING | ERROR
```

---

## 서버 실행

```bash
# 로컬 개발
APP_ENV=local uv run python main.py server

# 개발 서버
APP_ENV=dev uv run python main.py server

# 프로덕션
APP_ENV=prod uv run python main.py server
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
| `get_time` | — | 현재 시간 + 요일 |
| `calculate` | `expression` | 수식 계산 (AST 기반, eval 미사용) |
| `ping_server` | `url` | 서버 응답 시간 측정 |

---

## 인증

HTTP transport 사용 시 모든 요청에 JWT Bearer 토큰이 필요합니다.

```bash
# 토큰 발급
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# 응답
# {"access_token": "eyJ...", "token_type": "bearer", "expires_in": 1800}
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

```bash
APP_ENV=local uv run python main.py server
```

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

## 아키텍처

```
src/
├── core/
│   ├── config.py       # APP_ENV 기반 환경변수 관리 (pydantic-settings)
│   ├── logging.py      # JSON 구조화 로그 + tool_logger 데코레이터
│   └── auth.py         # JWT 토큰 생성·검증·미들웨어 클래스
├── auth/
│   └── setup.py        # /health, /auth/token, /auth/refresh 라우트 등록
├── weather/            # 날씨 도메인 (2 tools, 2 resources, 2 prompts)
├── news/               # 뉴스 도메인 (3 tools, 2 resources, 2 prompts)
├── database/           # DB 도메인 (11 tools, 2 resources, 1 prompt)
└── utils/              # 유틸리티 도메인 (3 tools)

src/app.py              # 도메인 조합 — 4개 mcp를 mount해 단일 서버 구성
main.py                 # CLI 진입점

tests/
├── unit/               # FastMCP Client 기반 단위 테스트
└── integration/        # PostgreSQL 필요 통합 테스트
```

---

## 문제 해결

**API 키 없이 테스트** — `demo_key` 유지 시 날씨·뉴스 도구가 샘플 데이터를 반환합니다.

**DB 연결 오류** — `DATABASE_URL`이 올바른지 확인하고, PostgreSQL이 실행 중인지 점검합니다.

**패키지 재설치**
```bash
uv cache clean && uv sync --reinstall
```

**로그 상세 확인** — `.env.local`에서 `LOG_LEVEL=DEBUG` 설정 후 재실행합니다.
