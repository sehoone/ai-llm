"""skill 도메인 테이블 (ADR-0024). schema: llmonl.

- `skill`: 재사용 지침 프리셋. `body`를 chat system prompt에 합성한다(ChatService).
  정식 Anthropic agent-skills(코드 실행)가 아니라 경량 지침 번들이다(ADR-0024 Context).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import NaiveDatetime
from sqlmodel import Field, SQLModel


def _uuid() -> str:
    return str(uuid.uuid4())


class Skill(SQLModel, table=True):
    __tablename__ = "skill"
    __table_args__ = {"schema": "llmonl"}

    id: str = Field(default_factory=_uuid, primary_key=True)
    user_id: int = Field(index=True)
    name: str
    description: str | None = Field(default=None)
    body: str = Field(default="")
    icon: str = Field(default="sparkles")
    color: str = Field(default="#6366f1")
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
    updated_at: NaiveDatetime | None = Field(default=None)
