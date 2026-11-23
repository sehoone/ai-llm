"""DB 엔진·세션. schema: llmonl (V2 계승)."""

import logging
from collections.abc import Generator

from sqlalchemy import text
from sqlmodel import Session, create_engine

from src.core.config import settings

logger = logging.getLogger(__name__)

# search_path를 llmonl로 고정 (orchestrator 테이블과 동일 스키마 공유)
# connect_timeout: DB가 응답 없을 때 무한 대기(기동 hang) 대신 빠르게 실패하도록 상한.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=1800,
    connect_args={"options": "-csearch_path=llmonl,public", "connect_timeout": 10},
)


def _masked_url() -> str:
    """비밀번호를 가린 연결 좌표 — 로그용."""
    return (
        f"postgresql://{settings.postgres_user}:***"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )


def check_connection() -> None:
    """기동 시 DB 연결을 1회 점검. 실패하면 좌표·사유를 로깅하고 예외를 올린다(fail-fast)."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error("DB 연결 실패: %s — %s: %s", _masked_url(), type(exc).__name__, exc)
        raise
    logger.info("DB 연결 성공: %s", _masked_url())


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
