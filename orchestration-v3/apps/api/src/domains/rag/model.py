"""rag 도메인 테이블 (ADR-0012 §3). schema: llmonl.

- `rag_group_config` / `rag_key_config`: UI 그룹·키 메타.
- `document`: 업로드 원문.
- `rag_embedding`(vector 1536)은 raw SQL로만 다루므로 ORM 모델을 두지 않는다(pgvector 타입 — repository).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import NaiveDatetime
from sqlmodel import Field, SQLModel


def _uuid() -> str:
    return str(uuid.uuid4())


class RagGroupConfig(SQLModel, table=True):
    __tablename__ = "rag_group_config"
    __table_args__ = {"schema": "llmonl"}

    id: str = Field(default_factory=_uuid, primary_key=True)
    user_id: int = Field(index=True)
    name: str = Field(index=True)
    description: str | None = Field(default=None)
    color: str = Field(default="#6366f1")
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
    updated_at: NaiveDatetime | None = Field(default=None)


class RagKeyConfig(SQLModel, table=True):
    __tablename__ = "rag_key_config"
    __table_args__ = {"schema": "llmonl"}

    id: str = Field(default_factory=_uuid, primary_key=True)
    user_id: int = Field(index=True)
    rag_key: str = Field(index=True)
    rag_group: str = Field(index=True)
    description: str | None = Field(default=None)
    rag_type: str = Field(default="chatbot_shared")
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
    updated_at: NaiveDatetime | None = Field(default=None)


class Document(SQLModel, table=True):
    __tablename__ = "document"
    __table_args__ = {"schema": "llmonl"}

    id: int | None = Field(default=None, primary_key=True)
    user_id: int | None = Field(default=None, index=True)  # NULL = chatbot_shared
    rag_key: str = Field(index=True)
    rag_group: str = Field(index=True)
    rag_type: str
    filename: str
    content: str
    doc_metadata: str | None = Field(default=None)
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
    updated_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
