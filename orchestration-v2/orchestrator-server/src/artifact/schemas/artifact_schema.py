"""Pydantic schemas for the artifact API."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ArtifactVersionResponse(BaseModel):
    """A single artifact version snapshot."""

    version: int = Field(..., description="Version number (1-based)")
    content: str = Field(..., description="Full artifact content for this version")
    created_at: datetime = Field(..., description="When this version was created")


class ArtifactSummary(BaseModel):
    """Artifact metadata without content — for list views."""

    id: str = Field(..., description="Artifact ID (uuid)")
    session_id: str = Field(..., description="Owning session ID")
    identifier: str = Field(..., description="LLM-provided identifier, unique within the session")
    artifact_type: str = Field(..., description="Artifact type, e.g. text/html")
    title: str = Field(..., description="Display title")
    current_version: int = Field(..., description="Latest version number")
    is_published: bool = Field(..., description="Whether a public link exists")
    public_token: Optional[str] = Field(default=None, description="Public share token, if published")
    created_at: datetime = Field(..., description="When the artifact was first created")
    updated_at: datetime = Field(..., description="When the artifact was last updated")


class ArtifactDetail(ArtifactSummary):
    """Artifact metadata plus the content of its current version."""

    content: str = Field(..., description="Content of the current version")


class ArtifactListResponse(BaseModel):
    """A list of artifact summaries."""

    items: List[ArtifactSummary] = Field(default_factory=list)


class ArtifactVersionListResponse(BaseModel):
    """All versions of an artifact."""

    items: List[ArtifactVersionResponse] = Field(default_factory=list)


class PublishResponse(BaseModel):
    """Result of publishing an artifact."""

    public_token: str = Field(..., description="Token for the public URL")
    is_published: bool = Field(default=True)


class PublicArtifactResponse(BaseModel):
    """Public (unauthenticated) view of a published artifact's current version."""

    title: str = Field(..., description="Display title")
    artifact_type: str = Field(..., description="Artifact type, e.g. text/html")
    content: str = Field(..., description="Content of the current version")
    version: int = Field(..., description="Current version number")


class ArtifactDataResponse(BaseModel):
    """Stored interactive data (user input) for an artifact."""

    data: Dict[str, Any] = Field(default_factory=dict)


class ArtifactDataUpdate(BaseModel):
    """Payload to replace an artifact's interactive data."""

    data: Dict[str, Any] = Field(default_factory=dict)
