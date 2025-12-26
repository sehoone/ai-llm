"""RAG API schemas."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    """Response model for document."""

    id: int
    filename: str
    user_id: Optional[int] = None
    size: int
    created_at: datetime


class RAGSearchResult(BaseModel):
    """Single RAG search result."""

    doc_id: int
    filename: str
    content: str  # Chunk of the document
    similarity: float  # Similarity score (0-1)


class RAGSearchResponse(BaseModel):
    """Response model for RAG search."""

    query: str
    results: List[RAGSearchResult]
