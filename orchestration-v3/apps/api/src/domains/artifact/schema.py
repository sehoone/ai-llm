"""artifact 도메인 DTO (ADR-0013). web `types/chat-api.ts`·`api/artifacts.ts` 계약과 정렬.

session_id는 web 호환 위해 문자열로 노출(chat 세션과 동일 패턴).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.domains.artifact.model import Artifact, ArtifactVersion


class ArtifactSummary(BaseModel):
    id: str
    session_id: str
    identifier: str
    artifact_type: str
    title: str
    current_version: int
    is_published: bool
    public_token: str | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, a: Artifact) -> "ArtifactSummary":
        return cls(
            id=a.id, session_id=str(a.session_id), identifier=a.identifier,
            artifact_type=a.artifact_type, title=a.title, current_version=a.current_version,
            is_published=a.is_published, public_token=a.public_token,
            created_at=a.created_at, updated_at=a.updated_at,
        )


class ArtifactDetail(ArtifactSummary):
    content: str

    @classmethod
    def from_models(cls, a: Artifact, content: str) -> "ArtifactDetail":
        return cls(**ArtifactSummary.from_model(a).model_dump(), content=content)


class ArtifactListResponse(BaseModel):
    items: list[ArtifactSummary] = Field(default_factory=list)


class ArtifactVersionResponse(BaseModel):
    version: int
    content: str
    created_at: datetime

    @classmethod
    def from_model(cls, v: ArtifactVersion) -> "ArtifactVersionResponse":
        return cls(version=v.version, content=v.content, created_at=v.created_at)


class ArtifactVersionListResponse(BaseModel):
    items: list[ArtifactVersionResponse] = Field(default_factory=list)


class PublishResponse(BaseModel):
    public_token: str
    is_published: bool = True


class PublicArtifactResponse(BaseModel):
    title: str
    artifact_type: str
    content: str
    version: int


class ArtifactDataResponse(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)


class ArtifactDataUpdate(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)
