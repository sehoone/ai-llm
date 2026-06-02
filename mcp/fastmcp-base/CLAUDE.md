# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
APP_ENV=local uv run python main.py server

# MCP Inspector — stdio 모드 (서버 별도 실행 불필요, 토큰 불필요)
MCP_TRANSPORT=stdio APP_ENV=local uv run fastmcp dev inspector src/app.py

# MCP Inspector — StreamableHTTP 모드 (터미널 두 개 필요)
# 터미널 1: APP_ENV=local uv run python main.py server
# 터미널 2: APP_ENV=local uv run fastmcp dev inspector src/app.py
# → Inspector UI: Transport=StreamableHTTP, URL=http://localhost:8000/mcp, Headers에 JWT 토큰 추가

# Tests
uv run pytest tests/unit/          # 단위 테스트 (API 키 / DB 불필요)
uv run pytest tests/integration/   # 통합 테스트 (PostgreSQL 필요)
uv run pytest tests/unit/test_foo.py::test_bar  # 단일 테스트

# Lint & format
black src/ tests/ main.py
isort src/ tests/ main.py
flake8 src/ tests/ main.py

# Docker (deploy/ 디렉토리에서 실행)
docker compose up --build                                  # 기본 (mcp + postgres)
docker compose --profile monitoring up --build             # + Loki/Grafana
docker compose --profile nginx up --build                  # + Nginx 리버스 프록시
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile nginx up -d --build  # 프로덕션
```

## Architecture

도메인 기반 구조 — 단일 FastMCP 인스턴스에 모든 도구를 등록합니다.

```
src/
├── core/                  # 공통 인프라 (도메인 무관)
│   ├── mcp.py             # 단일 FastMCP 인스턴스 + DB/HTTP lifespan
│   ├── config.py          # pydantic-settings 환경변수 관리 (APP_ENV 파일 분리)
│   ├── logging.py         # get_logger(name), tool_logger 데코레이터
│   ├── auth.py            # JWT 생성·검증, JWTAuthMiddleware, @protected, require_auth
│   ├── db.py              # async engine factory, session factory, test_connection
│   ├── http.py            # create_http_client, request_with_retry (지수 백오프)
│   ├── middleware.py      # RequestIDMiddleware — X-Request-ID 헤더 전파
│   └── context.py         # request_id_var (ContextVar) — 로거가 읽어 JSON 로그에 삽입
├── auth/
│   └── setup.py           # /health, /auth/token, /auth/refresh 등록 + rate limiter
├── weather/               # 날씨 도메인 (tools / resources / prompts / models)
├── news/                  # 뉴스 도메인
├── users/                 # 사용자/게시글 도메인 (SQLAlchemy ORM 포함)
├── utils/                 # get_time, calculate, ping_server
└── sample/                # 학습용 참조 구현 (app.py 미등록 — 필요 시 직접 추가)
    ├── basic/             # 케이스 01: Tool·Resource·Prompt 기초, 인메모리 CRUD
    ├── external_api/      # 케이스 02: httpx AsyncClient, 데모 모드, 예외 처리 체인
    ├── database/          # 케이스 03: SQLAlchemy async CRUD, flush→refresh→commit
    ├── context/           # 케이스 04: ctx.info/warning/error, report_progress, lifespan_context
    └── auth/              # 케이스 05: @protected, require_auth, 선택적 인증, RBAC

src/app.py                 # 도메인 모듈 import → @mcp.tool() 데코레이터 실행 → 등록 트리거
src/asgi.py                # ASGI 진입점 — Prometheus/RequestID 미들웨어, rate limiter, /metrics
main.py                    # CLI: "python main.py server" → uvicorn("src.asgi:app") 실행

tests/
├── unit/                  # FastMCP Client 기반 단위 테스트 (API 키 / DB 불필요)
└── integration/           # PostgreSQL 필요 통합 테스트
```

## Key patterns

**단일 인스턴스**: `src/core/mcp.py`에 `mcp = FastMCP(...)` 하나. 모든 도메인 파일이 `from src.core.mcp import mcp`로 import해 동일 인스턴스에 등록.

**도구 등록 트리거**: `app.py`가 각 도메인 모듈을 import하는 시점에 `@mcp.tool()` 데코레이터가 실행되어 등록됨. `# noqa: F401`로 lint 경고 억제. `sample/` 아래 도구는 `app.py`에 미등록 — 사용하려면 직접 추가.

**도메인 확장**: 새 도메인 추가 시 `tools.py`에서 `from src.core.mcp import mcp` 후 `@mcp.tool()` 등록, `app.py`에 import 한 줄 추가.

**데코레이터 적용 순서**:
```python
@mcp.tool()        # 가장 바깥 — FastMCP가 tool로 등록
@tool_logger(logger, param_keys=["city"])  # 중간 — 실행 로그 래퍼
@protected         # 가장 안쪽 — 인증 검사 후 원본 함수 호출
async def my_tool(city: str, ctx: Context) -> dict:
    ...
```

**Lifespan + Context**: `src/core/mcp.py`의 lifespan에서 DB 엔진(`db_session`)과 HTTP 클라이언트(`http_client`) 초기화 → `ctx.lifespan_context["db_session"]`으로 도구에 주입. `ctx`를 받을 수 없는 `custom_route` 핸들러에서는 `get_lifespan_context()`로 동일 dict 접근.

**DB session**: async SQLAlchemy + asyncpg. `async with session_factory() as db:` 패턴. 쓰기 시 `db.flush()` → `db.refresh(obj)` → `db.commit()` 순서.

**HTTP 클라이언트**: 외부 API 호출 시 lifespan에서 생성한 공유 `httpx.AsyncClient` 사용 권장. 재시도가 필요하면 `core/http.py`의 `request_with_retry` 사용 (5xx·연결 오류만 재시도, 지수 백오프).

**Error handling**: `ToolError` (fastmcp.exceptions) raise — dict 반환 대신 MCP 프로토콜 수준 에러. `ToolError`는 `tool_logger`에서 warning으로 기록(스택 없음), 일반 Exception은 exception으로 기록.

**인증 (HTTP transport)**:
- `auth_mode = "global"` (기본): `JWTAuthMiddleware`가 모든 MCP 요청을 차단. `/health`, `/auth/token`, `/auth/refresh`, `/metrics`는 bypass.
- `auth_mode = "per-tool"`: 미들웨어는 토큰 파싱만, `@protected` 또는 `require_auth(ctx)` 도구가 직접 검증.
- `verify_user`는 평문 비밀번호와 bcrypt 해시 모두 지원.
- `/auth/token`은 slowapi로 5회/1분 rate limit 적용.

**Testing**: `from src.app import mcp` 후 `async with Client(mcp) as client: await client.call_tool(...)` — in-memory 전체 스택 테스트. 에러 검증은 `raise_on_error=False` 후 `result.is_error` 확인. `pyproject.toml`에 `asyncio_mode = "auto"` 설정으로 `@pytest.mark.asyncio` 생략 가능.

**Demo mode**: `OPENWEATHER_API_KEY=demo_key` 또는 `NEWS_API_KEY=demo_key` 시 샘플 데이터 반환. `is_demo: True` 필드로 구분.

**Observability**: 모든 로그는 JSON 구조화 로그 (stdout). 각 로그 항목에 `request_id`가 자동 포함 (`RequestIDMiddleware` → `request_id_var` → `_JsonFormatter`). Prometheus 메트릭은 `/metrics` 엔드포인트 (JWT 인증 없이 스크래핑 가능).
