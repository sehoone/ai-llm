from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from src.core.config import get_settings
from src.core.logging import get_logger

logger = get_logger("database.session")

_engine = None
_SessionFactory = None


def _get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(settings.database_url, pool_pre_ping=True)
        logger.info("db_engine_created", extra={"url": settings.database_url.split("@")[-1]})
    return _engine


def _get_session_factory():
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(bind=_get_engine(), autocommit=False, autoflush=False)
    return _SessionFactory


@contextmanager
def get_session() -> Generator[Session, None, None]:
    session = _get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error("db_session_rollback", extra={"error": str(e)})
        raise
    finally:
        session.close()


def test_connection() -> bool:
    try:
        with get_session() as session:
            session.execute(text("SELECT 1"))
        logger.info("db_connection_ok")
        return True
    except Exception as e:
        logger.error("db_connection_failed", extra={"error": str(e)})
        return False
