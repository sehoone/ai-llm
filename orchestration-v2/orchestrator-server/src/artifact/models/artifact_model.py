"""Artifact models — a logical artifact and its immutable version snapshots."""

from datetime import UTC, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Artifact(SQLModel, table=True):
    """A logical artifact: the stable identity across all its versions.

    An artifact is scoped to a chat session and uniquely addressed within that
    session by ``identifier`` (the kebab-case id the LLM emits). Editing an
    artifact appends a new :class:`ArtifactVersion` and bumps ``current_version``.
    """

    __tablename__ = "artifact"

    id: str = Field(primary_key=True)  # uuid
    session_id: str = Field(index=True)
    user_id: int = Field(index=True)
    identifier: str = Field(index=True)  # LLM-provided, unique within a session
    artifact_type: str = Field(nullable=False)
    title: str = Field(default="")
    current_version: int = Field(default=1)
    is_published: bool = Field(default=False)
    public_token: Optional[str] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ArtifactVersion(SQLModel, table=True):
    """An immutable snapshot of an artifact's content at a point in time."""

    __tablename__ = "artifact_version"

    id: Optional[int] = Field(default=None, primary_key=True)
    artifact_id: str = Field(index=True)
    version: int = Field(nullable=False)
    content: str = Field(nullable=False)
    message_id: Optional[int] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ArtifactData(SQLModel, table=True):
    """Mutable, non-versioned key-value state for an interactive artifact.

    Holds end-user input (e.g. a settlement form) as a JSON string, one row per
    artifact, shared across all versions. Read/written through the host bridge so
    the sandbox itself never needs network access.
    """

    __tablename__ = "artifact_data"

    artifact_id: str = Field(primary_key=True)
    data: str = Field(default="{}", nullable=False)  # JSON-encoded object
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
