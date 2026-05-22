from contextlib import asynccontextmanager

from fastmcp import FastMCP

# 라이프스팬 동안 채워지는 공유 컨텍스트 — /health 같은 라우트와 MCP 도구에서 접근
_lifespan_context: dict = {}


@asynccontextmanager
async def _lifespan(server):
    yield _lifespan_context


mcp = FastMCP("FastMCP Base", lifespan=_lifespan)
