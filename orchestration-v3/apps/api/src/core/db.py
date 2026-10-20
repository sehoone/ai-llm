"""DB 엔진·세션. schema: llmonl (V2 계승)."""

from collections.abc import Generator

from sqlmodel import Session, create_engine

from src.core.config import settings

# search_path를 llmonl로 고정 (orchestrator 테이블과 동일 스키마 공유)
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=1800,
    connect_args={"options": "-csearch_path=llmonl,public"},
)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
