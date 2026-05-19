# CLAUDE.md

## Commands

```bash
# Install dependencies
uv sync

# 환경 설정 (최초 1회) — deploy/.env.example 참고
cp deploy/.env.example .env.local   # 로컬 개발
cp deploy/.env.example .env.dev     # 개발 서버
cp deploy/.env.example .env.prod    # 프로덕션

# DB 테이블 생성 (최초 1회)
psql -U postgres -d fastmcp_db -f scripts/schema.sql

# Run server — APP_ENV 로 환경 선택 (기본값: local)
APP_ENV=local uv run python main.py server   # 로컬
APP_ENV=dev   uv run python main.py server   # 개발 서버
APP_ENV=prod  uv run python main.py server   # 프로덕션

# MCP Inspector — stdio 모드 (서버 별도 실행 불필요, 토큰 불필요)
MCP_TRANSPORT=stdio APP_ENV=local uv run fastmcp dev inspector src/app.py
# → Inspector UI에서 Connect만 클릭

# MCP Inspector — StreamableHTTP 모드 (터미널 두 개 필요)
# 터미널 1: APP_ENV=local uv run python main.py server
# 터미널 2: APP_ENV=local uv run fastmcp dev inspector src/app.py
# → Inspector UI: Transport=StreamableHTTP, URL=http://localhost:8000/mcp, Headers에 JWT 토큰 추가

# Tests
uv run pytest tests/unit/          # 단위 테스트 (API 키 / DB 불필요)
uv run pytest tests/integration/   # 통합 테스트 (PostgreSQL 필요)
uv run pytest tests/               # 전체

# Lint & format
black src/ tests/ main.py
isort src/ tests/ main.py
flake8 src/ tests/ main.py
```

## Architecture

도메인 기반 구조 — 단일 FastMCP 인스턴스에 모든 도구를 등록합니다.

```
src/
├── core/                  # 공통 인프라 (도메인 무관)
│   ├── mcp.py             # 단일 FastMCP 인스턴스 + DB lifespan
│   ├── config.py          # pydantic-settings 환경변수 관리
│   ├── logging.py         # get_logger(name), tool_logger 데코레이터
│   ├── auth.py            # JWT 토큰 생성·검증·미들웨어 클래스
│   └── db.py              # async engine factory, session factory, test_connection
├── auth/                  # HTTP 인증 라우트
│   └── setup.py           # /health, /auth/token, /auth/refresh 등록 + 미들웨어 반환
├── weather/               # 날씨 도메인
│   ├── models.py          # WeatherResponse, ForecastResponse
│   ├── tools.py           # get_weather, get_forecast
│   ├── resources.py       # weather://supported-units, weather://demo-info
│   └── prompts.py         # weather_analysis, weather_comparison
├── news/                  # 뉴스 도메인
│   ├── models.py          # NewsResponse, Article, NewsSource
│   ├── tools.py           # get_top_headlines, search_news, get_news_sources
│   ├── resources.py       # news://categories, news://languages
│   └── prompts.py         # news_summary, daily_briefing
├── users/                 # 사용자/게시글 도메인
│   ├── models.py          # UserResponse, PostResponse 등 Pydantic 모델
│   ├── orm.py             # SQLAlchemy ORM (User, Post)
│   ├── tools.py           # CRUD 11개 도구
│   ├── resources.py       # db://schema, db://tables
│   └── prompts.py         # db_tool_guide
└── utils/                 # 유틸리티 도메인
    └── tools.py           # get_time, calculate, ping_server

src/app.py                 # 도메인 모듈 import → 도구 등록 트리거. mcp를 외부에 노출
src/asgi.py                # ASGI 진입점 — HTTP 배포 시 uvicorn이 이 파일을 로드
main.py                    # CLI 진입점 — src/asgi.py를 import string으로 참조해 실행

tests/
├── conftest.py            # 공통 pytest fixtures
├── unit/                  # FastMCP Client 기반 단위 테스트
└── integration/           # PostgreSQL 필요 통합 테스트
```

## Key patterns

**단일 인스턴스**: `src/core/mcp.py`에 `mcp = FastMCP(...)` 하나. 모든 도메인 파일이 `from src.core.mcp import mcp`로 import해 동일 인스턴스에 등록

**도구 등록 트리거**: `app.py`가 각 도메인 모듈을 import하는 시점에 `@mcp.tool()` 데코레이터가 실행되어 등록됨. `# noqa: F401`로 lint 경고 억제

**도메인 확장**: 새 도메인 추가 시 `tools.py`에서 `from src.core.mcp import mcp` 후 `@mcp.tool()` 등록, `app.py`에 import 한 줄 추가

**Tool registration**: `@mcp.tool()` 데코레이터 방식. `@tool_logger` 와 조합 시 내부 적용 후 외부 등록

**Lifespan + Context**: `src/core/mcp.py`의 lifespan에서 DB 엔진 초기화 → `ctx.lifespan_context["db_session"]`으로 database 도구에 주입

**DB session**: async SQLAlchemy + asyncpg. `async_sessionmaker` 로 세션 생성, `async with session() as db:` 패턴

**Error handling**: `ToolError` (fastmcp.exceptions) raise — dict 반환 대신 MCP 프로토콜 수준 에러

**Testing**: `from src.app import mcp` 후 `async with Client(mcp) as client: await client.call_tool(...)` — in-memory 전체 스택 테스트. 에러 검증은 `raise_on_error=False` 후 `result.is_error` 확인

**Demo mode**: API 키가 `demo_key` 이면 샘플 데이터 반환. `is_demo: True` 필드로 구분 가능

**Safe eval**: `utils/tools.py`의 `safe_eval()`은 `ast` 모듈 기반 — `eval()` 미사용
