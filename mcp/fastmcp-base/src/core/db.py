from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import Settings
from src.core.logging import get_logger

logger = get_logger("core.db")


def create_async_engine_from_settings(settings: Settings) -> AsyncEngine:
    url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    engine = create_async_engine(
        url,
        pool_pre_ping=True,
        pool_size=20,
        max_overflow=40,
        pool_recycle=3600,
        pool_timeout=30,
    )
    logger.info("db_async_engine_created", host=settings.database_url.split("@")[-1])
    return engine


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def test_connection(engine: AsyncEngine) -> bool:
    from sqlalchemy import text
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("db_connection_ok")
        return True
    except Exception as e:
        logger.error("db_connection_failed", error=str(e))
        return False
