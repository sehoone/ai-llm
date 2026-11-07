"""chat 도메인 테이블 (ADR-0008). schema: llmonl.

- `chat_session` / `chat_message`: 대화 영속.
- `chat_approval`: 승인 요청·결정의 감사 기록(재생방지·TTL·UI 이력).
  LangGraph 체크포인트와 **분리** — 체크포인트는 재개용, 이 테이블은 이력·인가용(ADR-0008 §5).
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import NaiveDatetime
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class ApprovalStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class ChatSession(SQLModel, table=True):
    __tablename__ = "chat_session"
    __table_args__ = {"schema": "llmonl"}

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    title: str = Field(default="New chat")
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
    updated_at: NaiveDatetime | None = Field(default=None)


class ChatMessage(SQLModel, table=True):
    __tablename__ = "chat_message"
    __table_args__ = {"schema": "llmonl"}

    id: int | None = Field(default=None, primary_key=True)
    session_id: int = Field(index=True)
    role: str  # "user" | "assistant" | "tool"
    content: str = Field(default="")
    # assistant의 tool_calls 또는 tool 메시지 메타 (JSONB)
    tool_calls: list[dict[str, Any]] | None = Field(default=None, sa_column=Column(JSONB))
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)


class ChatApproval(SQLModel, table=True):
    __tablename__ = "chat_approval"
    __table_args__ = {"schema": "llmonl"}

    id: int | None = Field(default=None, primary_key=True)
    session_id: int = Field(index=True)
    user_id: int = Field(index=True)
    group_key: str = Field(index=True)  # 한 번의 interrupt로 묶인 요청 묶음 식별자
    tool_call_id: str
    tool_name: str
    args: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB))
    tier: str = Field(default="CONFIRM")
    allow_edit: bool = Field(default=True)
    reason: str | None = Field(default=None)
    status: ApprovalStatus = Field(default=ApprovalStatus.PENDING)
    decided_by: int | None = Field(default=None)
    decided_at: NaiveDatetime | None = Field(default=None)
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
    expires_at: NaiveDatetime | None = Field(default=None)
