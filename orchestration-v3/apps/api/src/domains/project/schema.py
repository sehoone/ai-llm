"""project 도메인 DTO (ADR-0021). 비스트림 응답은 라우터에서 `ApiResponse[T]`로 감싼다."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from src.domains.project.model import Project


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    instructions: str = Field(default="")
    icon: str | None = None
    color: str | None = None


class ProjectUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    instructions: str | None = None
    icon: str | None = None
    color: str | None = None


class ProjectResponse(BaseModel):
    id: str
    user_id: int
    name: str
    description: str | None
    instructions: str
    rag_key: str
    rag_group: str
    icon: str
    color: str
    created_at: datetime
    updated_at: datetime | None

    @classmethod
    def from_model(cls, p: Project) -> "ProjectResponse":
        return cls(
            id=p.id,
            user_id=p.user_id,
            name=p.name,
            description=p.description,
            instructions=p.instructions,
            rag_key=p.rag_key,
            rag_group=p.rag_group,
            icon=p.icon,
            color=p.color,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )


class ProjectSessionResponse(BaseModel):
    """프로젝트 소속 대화(세션) — chat_session 투영."""

    id: int
    title: str


class ProjectKnowledgeItem(BaseModel):
    id: int
    filename: str


class KnowledgeUploadRequest(BaseModel):
    filename: str = Field(min_length=1)
    content: str = Field(min_length=1)
