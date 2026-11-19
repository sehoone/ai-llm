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


class ProjectSkill(SQLModel, table=True):
    """프로젝트 기본 활성 스킬 (ADR-0024 §4). 프로젝트 대화에 자동 적용된다.

    FK 없음(도메인 관례) — 연쇄 정리는 repository가 수행. `sort_order`로 합성 순서(우선순위) 보존.
    """

    __tablename__ = "project_skill"
    __table_args__ = {"schema": "llmonl"}

    project_id: str = Field(primary_key=True)
    skill_id: str = Field(primary_key=True)
    sort_order: int = Field(default=0)
