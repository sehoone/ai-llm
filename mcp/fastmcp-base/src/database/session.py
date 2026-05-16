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
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def test_connection() -> bool:
    try:
        with get_session() as session:
            session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False
