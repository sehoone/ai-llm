"""ai_overview 도메인 테이블. schema: llmonl.

- `ai_overview_document`: 사내 문서 원문 + 처리 상태.
- `ai_overview_keyword`: 문서별 LLM 생성 키워드/동의어 (trgm 검색 축).
- 벡터 축(`ai_overview_embedding`, vector 1536)은 raw SQL로만 다루므로 ORM 모델을 두지 않는다
  (pgvector 타입 — repository). rag 도메인과 동일한 규약.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import NaiveDatetime
from sqlmodel import Field, SQLModel


class AiOverviewDocument(SQLModel, table=True):
    __tablename__ = "ai_overview_document"
    __table_args__ = {"schema": "llmonl"}

    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(max_length=500)
    content: str
    source_url: str | None = Field(default=None, max_length=1000)
    status: str = Field(default="pending", max_length=20)  # pending|processing|ready|error
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
    updated_at: NaiveDatetime = Field(default_factory=datetime.utcnow)


class AiOverviewKeyword(SQLModel, table=True):
    __tablename__ = "ai_overview_keyword"
    __table_args__ = {"schema": "llmonl"}

    id: int | None = Field(default=None, primary_key=True)
    document_id: int = Field(index=True)
    keyword: str = Field(max_length=200)
    keyword_type: str = Field(max_length=20)  # keyword|synonym
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
