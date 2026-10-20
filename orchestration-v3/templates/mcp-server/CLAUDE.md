# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

orchestration-v3에서 **외부 시스템 연동용 MCP 서버**를 추가할 때 복사하는 템플릿. 복제 절차는 `README.md` 참고. 새 서버는 `apps/<name>-mcp/`에 둔다(ADR-0004).

> ⚠️ uv·ruff는 Claude 셸 PATH에 없을 수 있음 — lint/test/실행은 사용자가 직접.

## 핵심 원칙 (v3 컨벤션)

- **조직 축 = 도메인**: `apps/api`의 `domains/<d>/`와 같은 수직 슬라이스. 단, MCP 서버는 HTTP REST 경계도 `engine/`도 없으므로 **domains-lite**(tools·service·client·repository·models).
- **인증 자작 금지(ADR-0003)**: 자체 토큰 발급 없음. IdP 발급 토큰을 JWKS(RS256)로 **검증만**(`core/security.py`).
- **툴링**: uv + ruff + import-linter. `poe lint`가 레이어 경계(`domains → core` 단방향)까지 검사.
- **DB**: `llmonl` 스키마, psycopg3 async 엔진, `search_path=llmonl`. create_all 없음 → `scripts/schema.sql` 선적용.
- **설정**: 단일 `.env` (pydantic-settings), 모듈 레벨 `settings` 싱글턴.

## Commands

```bash
uv sync --group dev
cp .env.example .env

uv run fastmcp dev inspector src/app.py   # stdio Inspector (데모 모드, 인증 불필요)
uv run poe dev                            # HTTP :8000 (uvicorn src.asgi:app --reload)
uv run poe lint                           # ruff check + lint-imports(domains → core)
uv run poe format
uv run pytest tests/unit/
uv run pytest tests/unit/test_sample_domain.py::test_get_sample_item_demo_mode
```

## Architecture

단일 FastMCP 인스턴스에 모든 도구를 등록. 조직 축은 **도메인**이고, 외부 연동은 도메인 내부에서 **도구(얇음) → service(조합) → 어댑터(egress) → 외부 시스템**으로 흐른다.

```
src/
├─ core/           공통 인프라 (도메인 무관)
│  ├─ mcp.py       단일 FastMCP 인스턴스 + lifespan(async DB session factory·HTTP client 공유 주입)
│  ├─ config.py    pydantic-settings, 단일 .env. settings 싱글턴. 도메인별 설정 + is_demo_*
│  ├─ db.py        async 엔진(psycopg3) + session factory, search_path=llmonl
│  ├─ http.py      create_http_client · request_with_retry (5xx·연결오류만 지수백오프)
│  ├─ security.py  verify_token(JWKS/RS256) · OIDCAuthMiddleware · require_auth · @protected
│  ├─ logging.py   JSON 구조화 로그, tool_logger 데코레이터
│  ├─ middleware.py RequestIDMiddleware (X-Request-ID 전파)
│  └─ context.py   request_id ContextVar
├─ domains/<domain>/   도메인 수직 슬라이스 (= 확장 단위, domains-lite)
│  ├─ tools.py     @mcp.tool() — LLM 경계 (apps/api의 api 계층 대체). 얇게: service 호출·직렬화만
│  ├─ service.py   비즈니스 로직 — client/repository 어댑터 조합
│  ├─ client.py    REST egress: httpx 래퍼, request_with_retry 사용
│  ├─ repository.py DB egress: SQLAlchemy async 쿼리 (llmonl)
│  └─ models.py    pydantic 입출력 스키마 (schema 계층)
├─ app.py          도메인 tools import → @mcp.tool 등록 트리거
└─ asgi.py         ASGI 진입점 — /health custom_route + OIDC·RequestID 미들웨어 조립
main.py            CLI: stdio면 mcp.run, HTTP면 uvicorn("src.asgi:app")
```

## Key patterns

**단일 인스턴스**: `core/mcp.py`에 `mcp = FastMCP(...)` 하나. 모든 도메인이 `from src.core.mcp import mcp`로 동일 인스턴스에 등록.

**도구 등록 트리거**: `app.py`가 도메인 tools 모듈을 import하는 시점에 `@mcp.tool()`이 실행돼 등록. 새 도메인 = `app.py`에 import 한 줄.

**도메인 추가 (반복 작업 단위)**: `domains/sample/`을 복사 → `tools·service·client·repository·models` 교체(필요한 egress만) → `config.py`에 설정·`is_demo_*` → `app.py`에 등록.

**계층 책임**:
- `tools.py` — 입력 받아 service 호출, 결과 `model_dump()`. 가능한 한 로직 없음.
- `service.py` — 도메인 규칙·여러 어댑터 조합. demo 분기도 보통 여기.
- `client.py`/`repository.py` — 외부 egress만. HTTP 헤더·URL·재시도·SQL은 여기에 격리.
- 외부 호출용 httpx·DB 세션은 lifespan 공유 자원 — `ctx.lifespan_context["http_client"]` / `["db_session"]`.

**데코레이터 순서**:
```python
@mcp.tool()                                    # 바깥 — FastMCP 등록
@tool_logger(logger, param_keys=["item_id"])   # 중간 — 실행 로그
@protected                                     # 안쪽(선택) — IdP 토큰 검증 후 원본 호출
async def my_tool(item_id: str, ctx: Context) -> dict: ...
```

**데모 모드**: `config.py`의 `is_demo_*`가 참이면(api_key=demo_key) service가 외부 호출 없이 고정 데이터 반환. 클론 즉시 실행·테스트의 핵심. 새 도메인도 이 패턴을 따른다.

**에러 처리**: `ToolError`(fastmcp.exceptions) raise — dict 반환 대신 MCP 프로토콜 에러. httpx 예외는 service에서 ToolError로 변환. `tool_logger`는 ToolError를 warning(스택 생략), 일반 Exception은 exception으로 기록.

**DB**: async SQLAlchemy + psycopg3. `async with session_factory() as db:`. 쓰기 시 `flush → refresh → commit`. 테이블은 `llmonl` 스키마, **create_all 없음** — `scripts/schema.sql`로 사전 생성.

**인증 (ADR-0003 — 검증만)**: 자체 발급 없음. `AUTH_MODE=global`(기본)이면 `OIDCAuthMiddleware`가 모든 MCP 요청을 JWKS 검증(`/health`만 bypass). `per-tool`이면 미들웨어는 파싱만, `@protected`/`require_auth(ctx)`가 검증. **stdio transport는 HTTP 미들웨어 미적용** → 로컬 Inspector·테스트는 인증 없이 동작.

**Testing**: `from src.app import mcp` 후 `async with Client(mcp) as client: await client.call_tool(...)` — in-memory 전체 스택(HTTP 미들웨어·OIDC 미경유). 에러는 `raise_on_error=False` 후 `result.is_error`. DB 도구는 등록만 확인(실제 조회는 통합 테스트). `asyncio_mode="auto"`로 마커 생략.

**Observability**: stdout JSON 로그에 `request_id` 자동 포함(RequestIDMiddleware → ContextVar → formatter).
