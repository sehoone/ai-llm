from datetime import datetime
from enum import StrEnum

from sqlmodel import Field, SQLModel


class UserRole(StrEnum):
    SUPERADMIN = "SUPERADMIN"
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    CASHIER = "CASHIER"
    USER = "USER"


class User(SQLModel, table=True):
    """로컬 사용자 레코드. 인증은 IdP가 담당하고, 이 테이블은 JIT 프로비저닝으로 채워진다.

    - `idp_subject`: IdP 토큰 sub ↔ 로컬 BIGSERIAL id 매핑 키 (ADR-0003).
    - 정수형 `id`는 orchestrator 테이블들의 user_id FK로 그대로 쓰인다.
    - `hashed_password` 없음 — 비밀번호는 IdP 소유.
    """

    __tablename__ = "users"
    __table_args__ = {"schema": "llmonl"}

    id: int | None = Field(default=None, primary_key=True)
    idp_subject: str = Field(unique=True, index=True)
    username: str = Field(unique=True)
    email: str = Field(unique=True)
    role: UserRole = Field(default=UserRole.USER)
    status: str = Field(default="active")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = Field(default=None)
