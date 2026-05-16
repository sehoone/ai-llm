# CLAUDE.md

## Commands

```bash
# Install dependencies
uv sync

# Run server
uv run python main.py server integrated   # 통합 서버 (기본값)
uv run python main.py server weather
uv run python main.py server news
uv run python main.py server database

# DB 연결 확인
uv run python main.py init database

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

도메인 기반 구조 — 각 도메인이 모델·서버·인프라를 함께 소유합니다.

```
src/
├── core/                  # 공통 인프라 (도메인 무관)
│   ├── base.py            # BaseMCPServer 추상 클래스
│   ├── config.py          # pydantic-settings 환경변수 관리
│   ├── exceptions.py      # 공통 예외 클래스
│   └── logging.py         # get_logger(name) 유틸리티
├── weather/               # 날씨 도메인
│   ├── models.py          # WeatherResponse, ForecastResponse
│   └── server.py          # mcp 인스턴스 + get_weather, get_forecast
├── news/                  # 뉴스 도메인
│   ├── models.py          # NewsResponse, Article, NewsSource
│   └── server.py          # mcp 인스턴스 + get_top_headlines, search_news, get_news_sources
├── database/              # 데이터베이스 도메인
│   ├── models.py          # UserResponse, PostResponse 등 Pydantic 모델
│   ├── orm.py             # SQLAlchemy ORM (User, Post)
│   ├── session.py         # get_session() 컨텍스트 매니저
│   └── server.py          # mcp 인스턴스 + CRUD 10개 도구
└── integrated/            # 통합 서버
    └── server.py          # mcp 인스턴스 + 날씨·뉴스·유틸리티 통합

tests/
├── conftest.py            # 공통 pytest fixtures
├── unit/                  # API mock 기반 단위 테스트
└── integration/           # PostgreSQL 필요 통합 테스트
```

## Key patterns

**Config**: `get_settings()` (lru_cache) — `Settings.is_demo_weather/news` 로 데모 모드 판별

**Tool registration**: `mcp.tool()(fn)` 형식으로 파일 하단에서 명시적 등록 — 함수명이 유지되어 테스트에서 직접 호출 가능

**DB session**: `with get_session() as db:` 컨텍스트 매니저 (자동 commit/rollback/close)

**DB tools**: `asyncio.to_thread()` 로 sync SQLAlchemy 를 이벤트 루프 블로킹 없이 실행

**Error convention**: 모든 도구는 실패 시 `{"error": "message"}` 반환

**Demo mode**: API 키가 `demo_key` 이면 샘플 데이터 반환. `is_demo: True` 필드로 구분 가능

**Safe eval**: `integrated/server.py` 의 `safe_eval()` 은 `ast` 모듈 기반 — `eval()` 미사용
