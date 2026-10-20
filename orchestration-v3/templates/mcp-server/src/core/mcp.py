from contextlib import asynccontextmanager

from fastmcp import FastMCP

from src.core.db import create_engine, create_session_factory
from src.core.http import create_http_client

# 라이프스팬 동안 채워지는 공유 컨텍스트 — custom_route에서 ctx 없이 접근 시 사용
_lifespan_context: dict = {}


def get_lifespan_context() -> dict:
    """custom_route 등 Context를 받을 수 없는 곳에서 lifespan 컨텍스트에 접근하는 공개 접근자."""
    return _lifespan_context


# 서버 startup 시 한 번만 초기화해 모든 도구가 공유하는 자원(DB 세션 팩토리, HTTP 클라이언트)을 구성.
# yield 한 dict 가 각 도구의 ctx.lifespan_context 로 자동 주입된다.
#   도구: ctx.lifespan_context["db_session"] / ["http_client"]
# yield 뒤 finally 에서 Ctrl+C·예외에도 커넥션 풀·소켓을 반드시 닫는다.
@asynccontextmanager
async def lifespan(mcp: FastMCP):
    engine = create_engine()
    session_factory = create_session_factory(engine)
    http_client = create_http_client()

    _lifespan_context.update({"db_session": session_factory, "http_client": http_client})
    try:
        yield _lifespan_context
    finally:
        _lifespan_context.clear()
        await engine.dispose()
        await http_client.aclose()


mcp = FastMCP("MCP Server Template", lifespan=lifespan)
