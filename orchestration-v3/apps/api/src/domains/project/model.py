"""project 도메인 테이블 (ADR-0021). schema: llmonl.

- `project`: 대화·지침·지식을 묶는 작업공간. 대화는 chat 스택 재사용(`chat_session.project_id`),
  지식은 rag 전용 그룹 재사용(`rag_key`/`rag_group` 1:1 프로비저닝).

FK 없음 — 연쇄 정리는 앱(repository)이 명시 수행(chat·gpts 도메인 관례와 동일).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import NaiveDatetime
from sqlmodel import Field, SQLModel


def _uuid() -> str:
    return str(uuid.uuid4())


class Project(SQLModel, table=True):
    __tablename__ = "project"
    __table_args__ = {"schema": "llmonl"}

    id: str = Field(default_factory=_uuid, primary_key=True)
    user_id: int = Field(index=True)
    name: str
    description: str | None = Field(default=None)
    instructions: str = Field(default="")
    rag_key: str = Field(default_factory=lambda: f"project_{uuid.uuid4().hex}")
    rag_group: str = Field(default="")
    icon: str = Field(default="folder")
    color: str = Field(default="#6366f1")
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
    updated_at: NaiveDatetime | None = Field(default=None)
