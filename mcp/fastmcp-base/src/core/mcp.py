from contextlib import asynccontextmanager

from fastmcp import FastMCP

from src.core.config import get_settings
from src.core.db import create_async_engine_from_settings, create_session_factory


@asynccontextmanager
async def lifespan(mcp: FastMCP):
    engine = create_async_engine_from_settings(get_settings())
    session_factory = create_session_factory(engine)
    try:
        yield {"db_session": session_factory}
    finally:
        await engine.dispose()


mcp = FastMCP("FastMCP Base", lifespan=lifespan)
