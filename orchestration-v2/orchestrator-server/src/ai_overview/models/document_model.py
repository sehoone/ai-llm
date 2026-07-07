"""AI Overview document model."""

from datetime import datetime, UTC
from typing import Optional

from sqlmodel import Field, SQLModel


class AiOverviewDocument(SQLModel, table=True):
    __tablename__ = "ai_overview_document"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=500)
    content: str
    source_url: Optional[str] = Field(default=None, max_length=1000)
    status: str = Field(default="pending", max_length=20)  # pending | processing | ready | error
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
