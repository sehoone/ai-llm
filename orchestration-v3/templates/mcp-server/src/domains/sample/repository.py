"""[sample 도메인] DB egress 어댑터 (SQLAlchemy async).

쿼리를 여기에 격리한다. 세션은 lifespan 의 session_factory 에서 빌린다.
테이블은 llmonl 스키마(V3 공통). create_all 없음 → scripts/schema.sql 선적용 필요.
"""
from sqlalchemy import String, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SampleRecordORM(Base):
    __tablename__ = "sample_record"
    __table_args__ = {"schema": "llmonl"}

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    value: Mapped[str | None] = mapped_column(String(500), nullable=True)


async def find_records(
    session_factory: async_sessionmaker[AsyncSession], limit: int
) -> list[SampleRecordORM]:
    async with session_factory() as db:
        result = await db.execute(select(SampleRecordORM).limit(limit))
        return list(result.scalars().all())


async def count_records(session_factory: async_sessionmaker[AsyncSession]) -> int:
    async with session_factory() as db:
        result = await db.execute(select(func.count()).select_from(SampleRecordORM))
        return int(result.scalar_one())
