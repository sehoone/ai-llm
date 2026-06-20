from datetime import UTC, datetime
from typing import Any, Optional

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_log"
    __table_args__ = {"schema": "llmonl", "extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    occurred_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    # 요청자
    user_id: Optional[int] = None
    user_ip: Optional[str] = Field(default=None, max_length=45)
    request_id: Optional[str] = Field(default=None, max_length=36)
    user_agent: Optional[str] = Field(default=None, max_length=512)

    # 출처
    service: str = Field(default="orchestrator", max_length=20)

    # 액션
    action: str = Field(max_length=30)
    resource_type: str = Field(max_length=50)
    resource_id: Optional[str] = Field(default=None, max_length=255)

    # 변경 내용
    old_value: Optional[Any] = Field(default=None, sa_column=Column(JSONB))
    new_value: Optional[Any] = Field(default=None, sa_column=Column(JSONB))
    description: Optional[str] = Field(default=None, max_length=500)

    # 결과
    status: str = Field(default="SUCCESS", max_length=10)
    error_message: Optional[str] = None
