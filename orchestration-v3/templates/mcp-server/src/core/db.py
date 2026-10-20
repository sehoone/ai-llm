"""DB 엔진·세션 팩토리. schema: llmonl (V3 공통).

apps/api와 동일하게 psycopg 드라이버를 쓰되, MCP 도구가 async이므로 async 엔진을 사용한다.
search_path를 llmonl로 고정해 다른 V3 서비스와 같은 스키마를 공유한다.
"""

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger("core.db")


def create_engine() -> AsyncEngine:
    engine = create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_size=20,
        max_overflow=40,
        connect_args={"options": "-csearch_path=llmonl,public"},
    )
    logger.info("db_async_engine_created", extra={"db": settings.postgres_db})
    return engine


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
