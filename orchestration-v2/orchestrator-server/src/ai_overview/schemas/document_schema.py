"""Pydantic schemas for AI Overview document endpoints."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DocumentCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1)
    source_url: Optional[str] = Field(default=None, max_length=1000)


class KeywordResponse(BaseModel):
    id: int
    keyword: str
    keyword_type: str
    created_at: datetime


class DocumentSummaryResponse(BaseModel):
    id: int
    title: str
    source_url: Optional[str]
    status: str
    keyword_count: int
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    total: int
    items: list[DocumentSummaryResponse]


class DocumentDetailResponse(DocumentSummaryResponse):
    content: str
    keywords: list[KeywordResponse]
