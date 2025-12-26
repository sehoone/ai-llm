"""RAG embedding model for storing vector embeddings."""

from datetime import datetime, UTC
from typing import Any, Optional

from sqlmodel import (
    Column,
    Field,
)
from sqlalchemy import Text

from src.common.models.base import BaseModel


class RAGEmbedding(BaseModel, table=True):
    """RAG embedding model for storing document chunks with vector embeddings.

    Attributes:
        id: The primary key
        doc_id: Foreign key to the document
        rag_key: Key to identify which chatbot/RAG this embedding belongs to
        rag_group: Group identifier to fetch multiple RAGs together
        rag_type: Type of RAG - 'user_isolated' or 'chatbot_shared'
        chunk_index: Index of the chunk within the document
        content: The chunk content (text)
        embedding: The vector embedding (stored as pgvector vector type in DB, handled via raw SQL)
        created_at: When the embedding was created
    
    Note:
        The embedding field is defined as Any type because we use raw SQL for 
        insert/query operations with pgvector's vector type. SQLModel/Pydantic 
        doesn't natively support pgvector's Vector type.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    doc_id: int = Field(index=True)
    rag_key: str = Field(index=True)
    rag_group: str = Field(index=True)
    rag_type: str = Field(index=True)
    chunk_index: int
    content: str
    embedding: Optional[Any] = Field(default=None, sa_column=Column(Text))  # Actual type is vector(1536) in PostgreSQL
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
