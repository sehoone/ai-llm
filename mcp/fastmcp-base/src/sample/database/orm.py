"""
[케이스 03 - database] SQLAlchemy ORM 모델

다루는 패턴:
  - DeclarativeBase 상속
  - Mapped / mapped_column 타입 힌트 방식 (SQLAlchemy 2.x)
  - server_default로 DB 레벨 기본값 설정
  - 테이블 생성 SQL: scripts/schema.sql 에 추가 필요

CREATE TABLE IF NOT EXISTS products (
    id         SERIAL PRIMARY KEY,
    name       VARCHAR(200) NOT NULL,
    price      NUMERIC(12,2) NOT NULL DEFAULT 0,
    stock      INTEGER NOT NULL DEFAULT 0,
    category   VARCHAR(100) NOT NULL DEFAULT '기타',
    is_active  BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="기타")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
