"""skill 도메인 DTO (ADR-0024). 비스트림 응답은 라우터에서 `ApiResponse[T]`로 감싼다."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from src.domains.skill.model import Skill


class SkillCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    body: str = Field(min_length=1)
    icon: str | None = None
    color: str | None = None


class SkillUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    body: str | None = Field(default=None, min_length=1)
    icon: str | None = None
    color: str | None = None


class SkillResponse(BaseModel):
    id: str
    user_id: int
    name: str
    description: str | None
    body: str
    icon: str
    color: str
    created_at: datetime
    updated_at: datetime | None

    @classmethod
    def from_model(cls, s: Skill) -> "SkillResponse":
        return cls(
            id=s.id,
            user_id=s.user_id,
            name=s.name,
            description=s.description,
            body=s.body,
            icon=s.icon,
            color=s.color,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
