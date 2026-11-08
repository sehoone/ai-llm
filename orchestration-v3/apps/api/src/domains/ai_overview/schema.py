"""ai_overview DTO. web `src/api/ai-overview.ts` 인터페이스와 필드 정렬.

응답은 api 계층에서 `ApiResponse[T]`로 감싼다(axios 인터셉터가 자동 unwrap). 검색(`/search`)은
NDJSON 스트리밍이라 래퍼 미적용.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from src.domains.ai_overview.model import AiOverviewDocument, AiOverviewKeyword


# ── 요청 ──
class DocumentCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1)
    source_url: str | None = Field(default=None, max_length=1000)


class GenerateKeywordsRequest(BaseModel):
    system_prompt: str | None = None
    model: str | None = None  # (compat) v3는 llm_resource 기본 chat 리소스 사용 — 재매핑은 후속


class BatchDeleteRequest(BaseModel):
    ids: list[int]


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    model: str = ""          # (compat) 무시 — 기본 chat 리소스 사용
    system_prompt: str = ""


# ── 응답 ──
class KeywordResponse(BaseModel):
    id: int
    keyword: str
    keyword_type: str
    created_at: datetime

    @classmethod
    def from_model(cls, k: AiOverviewKeyword) -> "KeywordResponse":
        return cls(id=k.id, keyword=k.keyword, keyword_type=k.keyword_type, created_at=k.created_at)


class DocumentSummaryResponse(BaseModel):
    id: int
    title: str
    source_url: str | None
    status: str
    keyword_count: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, d: AiOverviewDocument, *, keyword_count: int) -> "DocumentSummaryResponse":
        return cls(
            id=d.id,
            title=d.title,
            source_url=d.source_url,
            status=d.status,
            keyword_count=keyword_count,
            created_at=d.created_at,
            updated_at=d.updated_at,
        )


class DocumentListResponse(BaseModel):
    total: int
    items: list[DocumentSummaryResponse]


class DocumentDetailResponse(DocumentSummaryResponse):
    content: str
    keywords: list[KeywordResponse]
