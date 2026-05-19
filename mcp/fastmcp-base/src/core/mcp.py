from contextlib import asynccontextmanager

import httpx
from fastmcp import FastMCP
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.core.config import get_settings
from src.core.db import create_async_engine_from_settings, create_session_factory
from src.core.http import create_http_client

# 라이프스팬 동안 채워지는 공유 컨텍스트 — /health 같은 custom route에서 접근
_lifespan_context: dict = {}


@asynccontextmanager
async def lifespan(mcp: FastMCP):
    settings = get_settings()
    engine = create_async_engine_from_settings(settings)
    session_factory = create_session_factory(engine)
    http_client = create_http_client(settings)
    _lifespan_context.update({"db_session": session_factory, "http_client": http_client})
    try:
        yield _lifespan_context
    finally:
        _lifespan_context.clear()
        await engine.dispose()
        await http_client.aclose()


mcp = FastMCP("FastMCP Base", lifespan=lifespan)
