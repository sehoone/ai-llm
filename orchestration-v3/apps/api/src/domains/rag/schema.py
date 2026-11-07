"""rag 도메인 DTO (ADR-0012). web `src/api/rag-groups.ts` 계약과 필드 정렬."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from src.domains.rag.model import Document, RagGroupConfig, RagKeyConfig


# ── 그룹 ──
class GroupCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    color: str | None = None


class GroupUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    color: str | None = None


class GroupResponse(BaseModel):
    id: str
    user_id: int
    name: str
    description: str | None
    color: str
    key_count: int
    doc_count: int
    created_at: datetime

    @classmethod
    def from_model(cls, g: RagGroupConfig, *, key_count: int, doc_count: int) -> "GroupResponse":
        return cls(
            id=g.id, user_id=g.user_id, name=g.name, description=g.description, color=g.color,
            key_count=key_count, doc_count=doc_count, created_at=g.created_at,
        )


# ── 키 ──
class KeyCreateRequest(BaseModel):
    rag_key: str = Field(min_length=1)
    rag_group: str = Field(min_length=1)
    description: str | None = None
    rag_type: str | None = None


class KeyUpdateRequest(BaseModel):
    rag_group: str | None = None
    description: str | None = None
    rag_type: str | None = None


class KeyResponse(BaseModel):
    id: str
    user_id: int
    rag_key: str
    rag_group: str
    description: str | None
    rag_type: str
    doc_count: int
    created_at: datetime

    @classmethod
    def from_model(cls, k: RagKeyConfig, *, doc_count: int) -> "KeyResponse":
        return cls(
            id=k.id, user_id=k.user_id, rag_key=k.rag_key, rag_group=k.rag_group,
            description=k.description, rag_type=k.rag_type, doc_count=doc_count, created_at=k.created_at,
        )


# ── 문서 ──
class DocumentUploadRequest(BaseModel):
    rag_key: str = Field(min_length=1)
    rag_group: str = Field(min_length=1)
    rag_type: str | None = None
    filename: str = Field(min_length=1)
    content: str = Field(min_length=1)


class DocumentResponse(BaseModel):
    id: int
    rag_key: str
    rag_group: str
    rag_type: str
    filename: str
    created_at: datetime

    @classmethod
    def from_model(cls, d: Document) -> "DocumentResponse":
        return cls(
            id=d.id, rag_key=d.rag_key, rag_group=d.rag_group, rag_type=d.rag_type,
            filename=d.filename, created_at=d.created_at,
        )


class DocumentUploadResponse(BaseModel):
    document: DocumentResponse
    chunks_indexed: int


# ── 검색 ──
class SearchRequest(BaseModel):
    rag_group: str = Field(min_length=1)
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)


class SearchResultItem(BaseModel):
    doc_id: int
    rag_key: str
    rag_group: str
    filename: str
    content: str
    chunk_index: int
    similarity: float
