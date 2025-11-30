"""This file contains the document model for RAG storage."""

from datetime import datetime, UTC
from typing import Optional

from sqlmodel import Field

from app.models.base import BaseModel


class Document(BaseModel, table=True):
    """Document model for storing RAG documents with embeddings.

    Attributes:
        id: The primary key
        user_id: The user ID who uploaded the document (NULL for chatbot_shared)
        rag_key: Key to identify which chatbot/RAG this document belongs to
        rag_group: Group identifier to fetch multiple RAGs together (e.g., 'support_bots')
        rag_type: Type of RAG - 'user_isolated' (per-user) or 'chatbot_shared' (global)
        filename: Original filename
        content: Document content (text)
        doc_metadata: JSON metadata (e.g., source, tags)
        created_at: When the document was created
        updated_at: When the document was last updated
    """

    id: int = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, index=True)  # NULL for chatbot_shared
    rag_key: str = Field(index=True)  # Key to identify chatbot/RAG
    rag_group: str = Field(index=True)  # Group to fetch multiple RAGs together
    rag_type: str = Field(index=True)  # 'user_isolated' or 'chatbot_shared'
    filename: str
    content: str = Field(index=False)  # Full text content
    doc_metadata: Optional[str] = Field(default=None)  # JSON string for metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
