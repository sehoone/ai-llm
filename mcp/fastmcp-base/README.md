# FastMCP Base

[FastMCP](https://gofastmcp.com) 기반의 멀티 도메인 MCP 서버 프로젝트

## 서버 목록

| 서버 | 설명 | MCP 도구 수 |
|---|---|---|
| `integrated` | 날씨 + 뉴스 + 유틸리티 통합 (기본값) | 8개 |
| `weather` | 날씨 전용 | 2개 |
| `news` | 뉴스 전용 | 3개 |
| `database` | PostgreSQL CRUD | 10개 |

---

## 요구사항

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) 패키지 매니저
- PostgreSQL (database 서버 사용 시)
- OpenWeatherMap API 키 (실제 날씨 데이터 사용 시)
- NewsAPI 키 (실제 뉴스 데이터 사용 시)

> API 키 없이도 `demo_key`로 설정하면 샘플 데이터로 동작합니다.

---

## 설치

```bash
# 의존성 설치
uv sync
```

---

## 환경변수 설정

`.env.example`을 복사하여 `.env`를 생성합니다.

```bash
cp .env.example .env
```

`.env` 주요 항목:

```ini
# API 키 (없으면 demo_key 유지 — 데모 데이터 반환)
OPENWEATHER_API_KEY=demo_key
NEWS_API_KEY=demo_key

# PostgreSQL 연결 문자열
DATABASE_URL=postgresql://postgres:password@localhost:5432/fastmcp_db

# MCP 서버 (기본값)
MCP_TRANSPORT=streamable-http
MCP_HOST=0.0.0.0
MCP_PORT=8000

# 로깅 레벨: DEBUG | INFO | WARNING | ERROR
LOG_LEVEL=INFO
```

---

## 실행

```bash
# 통합 서버 (기본값) — http://0.0.0.0:8000/mcp
uv run python main.py server integrated

# 날씨 서버
uv run python main.py server weather

# 뉴스 서버
uv run python main.py server news

# 데이터베이스 서버
uv run python main.py server database
```

서버 기동 시 출력 예시:
```
integrated MCP 서버를 시작합니다... [streamable-http] 0.0.0.0:8000
INFO  Starting MCP server 'Integrated MCP Server' with transport 'streamable-http' on http://0.0.0.0:8000/mcp
```

### Transport 방식 변경

```ini
# stdio 로 전환 (Claude Desktop 로컬 연결)
MCP_TRANSPORT=stdio
```

---

## 데이터베이스 초기화

```bash
# DB 연결 확인
uv run python main.py init database

# 테이블 생성 (users, posts)
uv run python main.py init tables
```

---

## MCP 도구 목록

### Weather (날씨)

| 도구 | 파라미터 | 설명 |
|---|---|---|
| `get_weather` | `city`, `country_code?` | 현재 날씨 조회 |
| `get_forecast` | `city`, `country_code?`, `days?=5` | 날씨 예보 (최대 5일) |

### News (뉴스)

| 도구 | 파라미터 | 설명 |
|---|---|---|
| `get_top_headlines` | `country?=kr`, `category?`, `page_size?=10` | 헤드라인 뉴스 |
| `search_news` | `query`, `language?=ko`, `sort_by?`, `page_size?=10` | 키워드 검색 |
| `get_news_sources` | `category?`, `language?=ko`, `country?=kr` | 뉴스 소스 목록 |

### Database (데이터베이스)

| 도구 | 파라미터 | 설명 |
|---|---|---|
| `create_user` | `username`, `email`, `full_name?` | 사용자 생성 |
| `get_users` | `limit?=10`, `offset?=0` | 사용자 목록 조회 |
| `get_user_by_id` | `user_id` | 사용자 상세 조회 (게시글 포함) |
| `create_post` | `title`, `content`, `author_id`, `is_published?=False` | 게시글 생성 |
| `get_posts` | `limit?=10`, `offset?=0`, `published_only?=False` | 게시글 목록 조회 |
| `update_post` | `post_id`, `title?`, `content?`, `is_published?` | 게시글 수정 |
| `delete_post` | `post_id` | 게시글 삭제 |
| `search_posts` | `query`, `limit?=10` | 게시글 검색 |
| `get_database_stats` | — | DB 통계 + 최근 활동 |
| `execute_raw_query` | `query`, `params?` | SELECT 전용 쿼리 실행 |

> `execute_raw_query`는 SELECT만 허용합니다. DROP/DELETE/UPDATE/INSERT/ALTER/TRUNCATE는 차단됩니다.

### Integrated (통합) 추가 도구

| 도구 | 파라미터 | 설명 |
|---|---|---|
| `get_time` | — | 현재 시간 + 요일 반환 |
| `calculate` | `expression` | 안전한 수식 계산 (AST 기반) |
| `ping_server` | `url` | 서버 응답 시간 측정 |

---

## 아키텍처

도메인 기반 구조 — 각 도메인이 모델·서버·인프라를 함께 소유합니다.

```
src/
├── core/                  # 공통 인프라
│   ├── base.py            # BaseMCPServer 추상 클래스
│   ├── config.py          # pydantic-settings 환경변수 관리
│   ├── exceptions.py      # 공통 예외 클래스
│   └── logging.py         # get_logger(name) 유틸리티
├── weather/               # 날씨 도메인
│   ├── models.py          # WeatherResponse, ForecastResponse
│   └── server.py          # mcp 인스턴스 + get_weather, get_forecast
├── news/                  # 뉴스 도메인
│   ├── models.py          # NewsResponse, Article, NewsSource
│   └── server.py          # mcp 인스턴스 + 3개 도구
├── database/              # 데이터베이스 도메인
│   ├── models.py          # UserResponse, PostResponse 등 Pydantic 모델
│   ├── orm.py             # SQLAlchemy ORM (User, Post)
│   ├── session.py         # get_session() 컨텍스트 매니저
│   └── server.py          # mcp 인스턴스 + 10개 도구
└── integrated/            # 통합 서버
    └── server.py          # 날씨·뉴스·유틸리티 통합

tests/
├── conftest.py            # 공통 pytest fixtures
├── unit/                  # API mock 기반 단위 테스트
│   ├── test_weather.py
│   ├── test_news.py
│   └── test_utils.py
└── integration/           # PostgreSQL 필요 통합 테스트
    └── test_database.py
```

### 데이터베이스 스키마

```
users
├── id           Integer PK
├── username     String(50) UNIQUE INDEX
├── email        String(100) UNIQUE INDEX
├── full_name    String(100)
├── is_active    Boolean (기본값 True)
└── created_at   DateTime

posts
├── id           Integer PK
├── title        String(200)
├── content      Text
├── is_published Boolean (기본값 False)
├── created_at   DateTime
├── updated_at   DateTime
└── author_id    Integer FK → users.id (cascade delete)
```

---

## 테스트

```bash
# 단위 테스트 (API 키 / DB 불필요)
uv run pytest tests/unit/

# 통합 테스트 (PostgreSQL 필요)
uv run pytest tests/integration/

# 전체 테스트
uv run pytest tests/
```

---

## 코드 품질

```bash
black src/ tests/ main.py
isort src/ tests/ main.py
flake8 src/ tests/ main.py
```

---

## 주요 패턴

**Config** — `get_settings()` (lru_cache), `Settings.is_demo_weather/news`로 데모 모드 판별

**Tool 등록** — `mcp.tool()(fn)` 형식으로 파일 하단에서 명시적 등록 → 함수명이 유지되어 테스트에서 직접 호출 가능

**DB 세션** — `with get_session() as db:` 컨텍스트 매니저 (자동 commit/rollback/close)

**비동기 DB** — `asyncio.to_thread()`로 sync SQLAlchemy를 이벤트 루프 블로킹 없이 실행

**에러 응답** — 모든 도구는 실패 시 `{"error": "message"}` 반환

**데모 모드** — API 키가 `demo_key`이면 샘플 데이터 반환, `is_demo: True` 필드로 구분

**Safe eval** — `integrated/server.py`의 `calculate()`는 AST 모듈 기반 (eval() 미사용)

---

## Claude Desktop 연동

`MCP_TRANSPORT=stdio`로 설정 후 Claude Desktop의 `claude_desktop_config.json`에 추가:

```json
{
  "mcpServers": {
    "fastmcp-integrated": {
      "command": "uv",
      "args": ["run", "python", "main.py", "server", "integrated"],
      "cwd": "/path/to/fastmcp-base"
    }
  }
}
```

`streamable-http` Transport 사용 시 서버를 먼저 기동한 뒤 URL로 연결:

```json
{
  "mcpServers": {
    "fastmcp-integrated": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

---

## 문제 해결

**API 키 없이 사용** — `demo_key` 유지 시 모든 날씨·뉴스 도구가 샘플 데이터를 반환합니다.

**DB 연결 실패** — `DATABASE_URL` 환경변수 확인 후 `uv run python main.py init database`로 진단합니다.

**패키지 재설치**
```bash
uv cache clean
uv sync --reinstall
```
