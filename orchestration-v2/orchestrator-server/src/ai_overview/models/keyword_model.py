"""AI Overview keyword/synonym model."""

from datetime import datetime, UTC
from typing import Optional

from sqlmodel import Field, SQLModel


class AiOverviewKeyword(SQLModel, table=True):
    __tablename__ = "ai_overview_keyword"

    id: Optional[int] = Field(default=None, primary_key=True)
    document_id: int = Field(index=True)
    keyword: str = Field(max_length=200)
    keyword_type: str = Field(max_length=20)  # 'keyword' | 'synonym'
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
