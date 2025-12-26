"""Document service for RAG operations."""

import json
from typing import Optional, List

from sqlmodel import (
    Session,
    select,
)

from src.common.logging import logger
from src.rag.models.document import Document
from src.common.services.database import database_service


class DocumentService:
    """Service for managing RAG documents."""

    def __init__(self):
        """Initialize document service."""
        self.db_service = database_service

    async def create_document(
        self, rag_key: str, rag_group: str, rag_type: str, filename: str, content: str, user_id: Optional[int] = None, doc_metadata: Optional[dict] = None
    ) -> Document:
        """Create a new document.

        Args:
            rag_key: The RAG key identifying which chatbot/RAG this belongs to
            rag_group: The RAG group for batch searches
            rag_type: Type of RAG - 'user_isolated' (per-user) or 'chatbot_shared' (global)
            filename: Original filename
            content: Document content (text)
            user_id: The user ID (required if rag_type is 'user_isolated', None for 'chatbot_shared')
            doc_metadata: Optional metadata dict

        Returns:
            Document: The created document
        """
        with Session(self.db_service.engine) as session:
            doc = Document(
                user_id=user_id,
                rag_key=rag_key,
                rag_group=rag_group,
                rag_type=rag_type,
                filename=filename,
                content=content,
                doc_metadata=json.dumps(doc_metadata) if doc_metadata else None,
            )
            session.add(doc)
            session.commit()
            session.refresh(doc)
            logger.info("document_created", doc_id=doc.id, rag_key=rag_key, rag_group=rag_group, rag_type=rag_type, filename=filename, user_id=user_id)
            return doc

    async def get_document(self, doc_id: int) -> Optional[Document]:
        """Get a document by ID.

        Args:
            doc_id: The document ID

        Returns:
            Optional[Document]: The document if found, None otherwise
        """
        with Session(self.db_service.engine) as session:
            doc = session.get(Document, doc_id)
            return doc

    async def get_user_documents(self, user_id: int, rag_key: Optional[str] = None, rag_type: Optional[str] = None) -> List[Document]:
        """Get all documents for a user, optionally filtered by RAG key and type.

        Args:
            user_id: The user ID
            rag_key: Optional RAG key filter
            rag_type: Optional RAG type filter ('user_isolated' or 'chatbot_shared')

        Returns:
            List[Document]: List of user's documents
        """
        with Session(self.db_service.engine) as session:
            statement = select(Document).where(Document.user_id == user_id)
            if rag_key:
                statement = statement.where(Document.rag_key == rag_key)
            if rag_type:
                statement = statement.where(Document.rag_type == rag_type)
            statement = statement.order_by(Document.created_at.desc())
            docs = session.exec(statement).all()
            return docs

    async def delete_document(self, doc_id: int) -> bool:
        """Delete a document by ID.

        Args:
            doc_id: The document ID to delete

        Returns:
            bool: True if deletion was successful, False if document not found
        """
        with Session(self.db_service.engine) as session:
            doc = session.get(Document, doc_id)
            if not doc:
                return False
            session.delete(doc)
            session.commit()
            logger.info("document_deleted", doc_id=doc_id)
            return True

    async def search_documents(self, user_id: int, query: str, limit: int = 10) -> List[Document]:
        """Search documents by user using full-text search.

        Args:
            user_id: The user ID
            query: Search query
            limit: Maximum number of results

        Returns:
            List[Document]: List of matching documents
        """
        with Session(self.db_service.engine) as session:
            # Simple full-text search (can be enhanced with PostgreSQL FTS)
            statement = (
                select(Document)
                .where(
                    (Document.user_id == user_id)
                    & (
                        (Document.content.contains(query))
                        | (Document.filename.contains(query))
                    )
                )
                .limit(limit)
            )
            docs = session.exec(statement).all()
            return docs


# Create singleton instance
document_service = DocumentService()
