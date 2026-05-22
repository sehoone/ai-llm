#!/usr/bin/env python3
"""FastMCP 베이스 프로젝트

uvicorn이 workers > 1로 동작할 때 각 워커는 이 파일을 직접 import해 app을 독립적으로 초기화한다.

    uvicorn.run("main:app", workers=4)  # 각 워커가 이 파일을 import
"""
import asyncio
import sys
from contextlib import asynccontextmanager
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI  # noqa: E402
from slowapi import _rate_limit_exceeded_handler  # noqa: E402
from slowapi.errors import RateLimitExceeded  # noqa: E402
from fastapi import Request  # noqa: E402
from fastapi.responses import Response  # noqa: E402
from starlette_prometheus import PrometheusMiddleware  # noqa: E402
from starlette_prometheus import metrics as prometheus_metrics  # noqa: E402

from src.app import mcp  # noqa: E402
from src.auth.setup import auth_router, limiter  # noqa: E402
from src.core.auth import JWTAuthMiddleware  # noqa: E402
from src.core.config import get_settings  # noqa: E402
from src.core.db import create_async_engine_from_settings, create_session_factory  # noqa: E402
from src.core.http import create_http_client  # noqa: E402
from src.core.logging import get_logger  # noqa: E402
from src.core.mcp import _lifespan_context  # noqa: E402
from src.core.middleware import RequestIDMiddleware  # noqa: E402

_logger = get_logger("main")
settings = get_settings()
mcp_app = mcp.http_app(transport=settings.mcp_transport)


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = create_async_engine_from_settings(settings)
    session_factory = create_session_factory(engine)
    http_client = create_http_client(settings)
    _lifespan_context.update({"db_session": session_factory, "http_client": http_client})
    # mcp_app의 lifespan을 명시적으로 실행 — FastAPI sub-mount 시 자동 호출되지 않음
    async with mcp_app.lifespan(mcp_app):
        try:
            yield
        finally:
            _lifespan_context.clear()
            await asyncio.shield(engine.dispose())
            await asyncio.shield(http_client.aclose())


app = FastAPI(title="FastMCP Base API", lifespan=lifespan)

# add_middleware: 마지막 호출이 가장 먼저 실행됨 (outermost)
# 실행 순서: JWTAuthMiddleware → PrometheusMiddleware → RequestIDMiddleware → handler
app.add_middleware(RequestIDMiddleware)
app.add_middleware(PrometheusMiddleware)
app.add_middleware(JWTAuthMiddleware, settings=settings)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(auth_router)


@app.get("/metrics", include_in_schema=False)
async def metrics_endpoint(request: Request) -> Response:
    return prometheus_metrics(request)


# MCP 앱을 루트에 마운트 — 위에 등록된 FastAPI 라우트가 먼저 매칭되고 나머지가 MCP로 전달
app.mount("/", mcp_app)


# ── CLI ────────────────────────────────────────────────────────────────────

_USAGE = """\
FastMCP 베이스 프로젝트

사용법:
    python main.py server    # 서버 실행 (날씨·뉴스·DB·유틸리티 전체 도구)
"""


def cmd_server() -> None:
    _logger.info(
        "server_starting",
        transport=settings.mcp_transport,
        host=settings.mcp_host,
        port=settings.mcp_port,
        workers=settings.mcp_workers,
    )

    if settings.mcp_transport in ("streamable-http", "http", "sse"):
        _run_http_server()
    else:
        mcp.run(transport=settings.mcp_transport)


def _run_http_server() -> None:
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.mcp_host,
        port=settings.mcp_port,
        workers=settings.mcp_workers,
        access_log=(settings.log_level == "DEBUG"),
        log_level=settings.log_level.lower(),
        timeout_keep_alive=30,
        timeout_graceful_shutdown=5,
    )


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in ("help", "--help", "-h"):
        print(_USAGE)
        return

    if args[0] == "server":
        try:
            cmd_server()
        except KeyboardInterrupt:
            print("\n종료합니다.")
    else:
        print(f"알 수 없는 명령어: {args[0]}")
        print(_USAGE)
        sys.exit(1)


if __name__ == "__main__":
    main()
