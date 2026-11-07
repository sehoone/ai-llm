from datetime import datetime
from enum import StrEnum

from pydantic import NaiveDatetime
from sqlmodel import Field, SQLModel


class UserRole(StrEnum):
    SUPERADMIN = "SUPERADMIN"
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    CASHIER = "CASHIER"
    USER = "USER"


class User(SQLModel, table=True):
    """로컬 사용자 레코드. 백엔드가 ID/PW를 직접 인증하고 비밀번호를 보관한다.

    - `hashed_password`: bcrypt 해시(자체 인증). API 키 전용 사용자는 None일 수 있다.
    - 정수형 `id`는 orchestrator 테이블들의 user_id FK로 그대로 쓰인다.
    - `idp_subject`: (비활성·보존) OIDC 복귀 시 IdP sub 매핑 키. 자체 인증에서는 null.
    """

    __tablename__ = "users"
    __table_args__ = {"schema": "llmonl"}

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True)
    email: str = Field(unique=True)
    hashed_password: str | None = Field(default=None)
    role: UserRole = Field(default=UserRole.USER)
    status: str = Field(default="active")
    idp_subject: str | None = Field(default=None, unique=True, index=True)
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
    updated_at: NaiveDatetime | None = Field(default=None)
