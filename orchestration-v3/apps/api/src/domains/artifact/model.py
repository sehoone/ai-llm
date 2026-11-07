"""artifact 도메인 테이블 (ADR-0013 §3). schema: llmonl. FK 없음 — 앱이 연쇄 정리."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import NaiveDatetime
from sqlmodel import Field, SQLModel


def _uuid() -> str:
    return str(uuid.uuid4())


class Artifact(SQLModel, table=True):
    __tablename__ = "artifact"
    __table_args__ = {"schema": "llmonl"}

    id: str = Field(default_factory=_uuid, primary_key=True)
    session_id: int = Field(index=True)
    user_id: int = Field(index=True)
    identifier: str = Field(index=True)  # LLM이 준 식별자(세션 내 고유)
    artifact_type: str
    title: str = Field(default="")
    current_version: int = Field(default=1)
    is_published: bool = Field(default=False)
    public_token: str | None = Field(default=None, index=True)
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
    updated_at: NaiveDatetime = Field(default_factory=datetime.utcnow)


class ArtifactVersion(SQLModel, table=True):
    __tablename__ = "artifact_version"
    __table_args__ = {"schema": "llmonl"}

    id: int | None = Field(default=None, primary_key=True)
    artifact_id: str = Field(index=True)
    version: int
    content: str
    message_id: int | None = Field(default=None, index=True)
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)


class ArtifactData(SQLModel, table=True):
    __tablename__ = "artifact_data"
    __table_args__ = {"schema": "llmonl"}

    artifact_id: str = Field(primary_key=True)
    data: str = Field(default="{}")
    updated_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
