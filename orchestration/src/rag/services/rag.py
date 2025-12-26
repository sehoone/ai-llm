"""RAG service for semantic search using pgvector."""

import asyncio
from typing import List, Optional

from langchain_openai import OpenAIEmbeddings
from sqlmodel import (
    Session,
    text,
)

from src.common.config import settings
from src.common.logging import logger
from src.common.services.database import database_service
from src.common.services.llm import llm_service
from src.chatbot.schemas.chat import Message


class RAGService:
    """Service for RAG operations using pgvector."""

    def __init__(self):
        """Initialize RAG service."""
        self.db_service = database_service
        self.llm_service = llm_service
        self._embeddings: Optional[OpenAIEmbeddings] = None
        self.chunk_size = 500  # Characters per chunk
        self.chunk_overlap = 100  # Overlap between chunks
        self.max_file_size = 10 * 1024 * 1024  # 10MB max file size
        self.max_chunks_per_batch = 3  # Reduced from 5 to save memory

    async def _get_embeddings(self) -> OpenAIEmbeddings:
        """Get or initialize OpenAI embeddings.

        Returns:
            OpenAIEmbeddings: Embeddings instance
        """
        if self._embeddings is None:
            self._embeddings = OpenAIEmbeddings(
                model="text-embedding-3-small",
                api_key=settings.OPENAI_API_KEY,
            )
        return self._embeddings

    def _chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks.

        Args:
            text: The text to chunk

        Returns:
            List[str]: List of text chunks
        """
        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            # Get chunk
            end = min(start + self.chunk_size, text_length)
            chunk = text[start:end]
            chunks.append(chunk)

            # If we've reached the end, break to avoid infinite loop
            if end >= text_length:
                break

            # Move start position with overlap
            # Ensure we always make progress
            new_start = end - self.chunk_overlap
            # If overlap would cause us to stay in same place or go backwards, move by at least 1
            if new_start <= start:
                start = start + max(1, self.chunk_size - self.chunk_overlap)
            else:
                start = new_start

        return chunks

    async def add_document_to_rag(self, doc_id: int, rag_key: str, rag_group: str, rag_type: str, content: str) -> bool:
        """Add a document to RAG with embeddings using pgvector.

        Args:
            doc_id: The document ID
            rag_key: The RAG key identifying which chatbot/RAG this belongs to
            rag_group: The RAG group for batch searches
            rag_type: Type of RAG - 'user_isolated' (per-user) or 'chatbot_shared' (global)
            content: The document content to embed

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check file size
            content_size = len(content.encode('utf-8'))
            if content_size > self.max_file_size:
                logger.error(
                    "document_too_large",
                    doc_id=doc_id,
                    size_mb=content_size / (1024 * 1024),
                    max_mb=self.max_file_size / (1024 * 1024),
                )
                return False

            # Split content into chunks
            chunks = self._chunk_text(content)
            chunk_count = len(chunks)
            logger.info(
                "document_chunked",
                doc_id=doc_id,
                rag_key=rag_key,
                rag_group=rag_group,
                rag_type=rag_type,
                chunk_count=chunk_count,
                content_size_mb=content_size / (1024 * 1024),
            )

            # Get embeddings instance
            embeddings = await self._get_embeddings()

            # Process chunks in smaller batches to save memory
            batch_size = self.max_chunks_per_batch
            for i in range(0, chunk_count, batch_size):
                batch = chunks[i : i + batch_size]
                logger.debug(
                    "processing_chunk_batch",
                    doc_id=doc_id,
                    batch_index=i,
                    batch_size=len(batch),
                    total_chunks=chunk_count,
                )

                # Get embeddings for batch
                try:
                    batch_embeddings = await embeddings.aembed_documents(batch)
                except Exception as e:
                    logger.error(
                        "failed_to_embed_batch",
                        doc_id=doc_id,
                        batch_index=i,
                        error=str(e),
                    )
                    # Continue with next batch even if current fails
                    continue

                # Store embeddings in database
                try:
                    with Session(self.db_service.engine) as session:
                        for chunk_idx, (chunk, embedding) in enumerate(zip(batch, batch_embeddings)):
                            embedding_str = f"[{','.join(map(str, embedding))}]"
                            try:
                                session.exec(
                                    text("""
                                    INSERT INTO rag_embedding (doc_id, rag_key, rag_group, rag_type, chunk_index, content, embedding, created_at)
                                    VALUES (:doc_id, :rag_key, :rag_group, :rag_type, :chunk_index, :content, CAST(:embedding AS vector), NOW())
                                    """),
                                    params={
                                        "doc_id": doc_id,
                                        "rag_key": rag_key,
                                        "rag_group": rag_group,
                                        "rag_type": rag_type,
                                        "chunk_index": i + chunk_idx,
                                        "content": chunk,
                                        "embedding": embedding_str,
                                    }
                                )
                            except Exception as e:
                                logger.error(
                                    "failed_to_insert_embedding",
                                    doc_id=doc_id,
                                    chunk_index=i + chunk_idx,
                                    error=str(e),
                                )
                        session.commit()
                except Exception as e:
                    logger.error(
                        "failed_to_store_batch",
                        doc_id=doc_id,
                        batch_index=i,
                        error=str(e),
                    )

                # Clear batch from memory
                del batch
                del batch_embeddings

                # Add delay between batches to avoid rate limiting and memory buildup
                if i + batch_size < chunk_count:
                    await asyncio.sleep(1.0)  # Increased delay for stability

            logger.info(
                "document_added_to_rag",
                doc_id=doc_id,
                rag_key=rag_key,
                rag_group=rag_group,
                rag_type=rag_type,
                total_chunks=chunk_count,
            )
            return True

        except Exception as e:
            logger.error(
                "failed_to_add_document_to_rag",
                doc_id=doc_id,
                error=str(e),
                exc_info=True,
            )
            return False

    async def search_rag(self, rag_key: str, rag_type: str, user_id: Optional[int] = None, query: str = "", limit: int = 5) -> List[dict]:
        """Search RAG documents using semantic similarity.

        Args:
            rag_key: The RAG key identifying which chatbot/RAG to search
            rag_type: Type of RAG - 'user_isolated' or 'chatbot_shared'
            user_id: The user ID (required if rag_type is 'user_isolated', ignored for 'chatbot_shared')
            query: The search query
            limit: Maximum number of results

        Returns:
            List[dict]: Search results with chunks and similarity scores
        """
        try:
            # Get query embedding
            embeddings = await self._get_embeddings()
            query_embedding = await embeddings.aembed_query(query)
            embedding_str = f"[{','.join(map(str, query_embedding))}]"

            # Search for similar chunks
            with Session(self.db_service.engine) as session:
                # Build query based on rag_type
                if rag_type == "user_isolated":
                    # User-specific search
                    if not user_id:
                        logger.error("user_id_required_for_user_isolated_rag")
                        return []
                    query_str = """
                    SELECT 
                        re.id,
                        re.doc_id,
                        d.filename,
                        re.content,
                        re.chunk_index,
                        1 - (re.embedding <=> CAST(:query_embedding AS vector)) as similarity
                    FROM rag_embedding re
                    JOIN document d ON re.doc_id = d.id
                    WHERE d.user_id = :user_id AND re.rag_key = :rag_key AND re.rag_type = :rag_type
                    ORDER BY re.embedding <=> CAST(:query_embedding AS vector)
                    LIMIT :limit
                    """
                    results = session.exec(
                        text(query_str),
                        params={
                            "user_id": user_id,
                            "rag_key": rag_key,
                            "rag_type": rag_type,
                            "query_embedding": embedding_str,
                            "limit": limit,
                        }
                    ).all()
                else:  # chatbot_shared
                    # Global search (no user filter)
                    query_str = """
                    SELECT 
                        re.id,
                        re.doc_id,
                        d.filename,
                        re.content,
                        re.chunk_index,
                        1 - (re.embedding <=> CAST(:query_embedding AS vector)) as similarity
                    FROM rag_embedding re
                    JOIN document d ON re.doc_id = d.id
                    WHERE re.rag_key = :rag_key AND re.rag_type = :rag_type
                    ORDER BY re.embedding <=> CAST(:query_embedding AS vector)
                    LIMIT :limit
                    """
                    results = session.exec(
                        text(query_str),
                        params={
                            "rag_key": rag_key,
                            "rag_type": rag_type,
                            "query_embedding": embedding_str,
                            "limit": limit,
                        }
                    ).all()

                output = []
                for row in results:
                    output.append({
                        "id": row[0],
                        "doc_id": row[1],
                        "filename": row[2],
                        "content": row[3],
                        "chunk_index": row[4],
                        "similarity": float(row[5]),
                    })

                logger.info("rag_search_completed", query_length=len(query), result_count=len(output))
                return output

        except Exception as e:
            logger.error("failed_to_search_rag", user_id=user_id, query=query, error=str(e), exc_info=True)
            return []

    async def search_rag_group(self, rag_group: str, rag_type: str, user_id: Optional[int] = None, query: str = "", limit: int = 5) -> List[dict]:
        """Search multiple RAGs within a group using semantic similarity.

        Args:
            rag_group: The RAG group identifier to search all RAGs in the group
            rag_type: Type of RAG - 'user_isolated' or 'chatbot_shared'
            user_id: The user ID (required if rag_type is 'user_isolated')
            query: The search query
            limit: Maximum number of results per RAG

        Returns:
            List[dict]: Search results from all RAGs in the group with chunks and similarity scores
        """
        try:
            # Get query embedding
            embeddings = await self._get_embeddings()
            query_embedding = await embeddings.aembed_query(query)
            embedding_str = f"[{','.join(map(str, query_embedding))}]"

            # Search for similar chunks in all RAGs of the group
            with Session(self.db_service.engine) as session:
                # Build query based on rag_type
                if rag_type == "user_isolated":
                    # User-specific search
                    if not user_id:
                        logger.error("user_id_required_for_user_isolated_rag")
                        return []
                    query_str = """
                    SELECT 
                        re.id,
                        re.doc_id,
                        re.rag_key,
                        re.rag_group,
                        d.filename,
                        re.content,
                        re.chunk_index,
                        1 - (re.embedding <=> CAST(:query_embedding AS vector)) as similarity
                    FROM rag_embedding re
                    JOIN document d ON re.doc_id = d.id
                    WHERE d.user_id = :user_id AND re.rag_group = :rag_group AND re.rag_type = :rag_type
                    ORDER BY re.embedding <=> CAST(:query_embedding AS vector)
                    LIMIT :limit
                    """
                    results = session.exec(
                        text(query_str),
                        params={
                            "user_id": user_id,
                            "rag_group": rag_group,
                            "rag_type": rag_type,
                            "query_embedding": embedding_str,
                            "limit": limit,
                        }
                    ).all()
                else:  # chatbot_shared
                    # Global search (no user filter)
                    query_str = """
                    SELECT 
                        re.id,
                        re.doc_id,
                        re.rag_key,
                        re.rag_group,
                        d.filename,
                        re.content,
                        re.chunk_index,
                        1 - (re.embedding <=> CAST(:query_embedding AS vector)) as similarity
                    FROM rag_embedding re
                    JOIN document d ON re.doc_id = d.id
                    WHERE re.rag_group = :rag_group AND re.rag_type = :rag_type
                    ORDER BY re.embedding <=> CAST(:query_embedding AS vector)
                    LIMIT :limit
                    """
                    results = session.exec(
                        text(query_str),
                        params={
                            "rag_group": rag_group,
                            "rag_type": rag_type,
                            "query_embedding": embedding_str,
                            "limit": limit,
                        }
                    ).all()

                output = []
                for row in results:
                    output.append({
                        "id": row[0],
                        "doc_id": row[1],
                        "rag_key": row[2],
                        "rag_group": row[3],
                        "filename": row[4],
                        "content": row[5],
                        "chunk_index": row[6],
                        "similarity": float(row[7]),
                    })

                logger.info("rag_group_search_completed", rag_group=rag_group, rag_type=rag_type, result_count=len(output))
                return output

        except Exception as e:
            logger.error("failed_to_search_rag_group", rag_group=rag_group, rag_type=rag_type, query=query, error=str(e), exc_info=True)
            return []

    async def augment_prompt_with_rag(
        self, rag_key: str, rag_type: str, user_id: Optional[int] = None, message: str = "", limit: int = 3
    ) -> str:
        """Augment a prompt with RAG context.

        Args:
            rag_key: The RAG key identifying which chatbot/RAG to use
            rag_type: Type of RAG - 'user_isolated' or 'chatbot_shared'
            user_id: The user ID (required if rag_type is 'user_isolated')
            message: The user message
            limit: Maximum number of chunks to include

        Returns:
            str: Augmented prompt with RAG context
        """
        # Search for relevant documents
        search_results = await self.search_rag(rag_key, rag_type, user_id, message, limit=limit)

        if not search_results:
            return message

        # Build context from top results
        context_chunks = [result["content"] for result in search_results]
        context = "\n\n".join(context_chunks)

        # Create augmented prompt
        augmented_prompt = f"""{message}

Context from documents:
{context}"""

        return augmented_prompt

    async def augment_prompt_with_rag_group(
        self, rag_group: str, rag_type: str, user_id: Optional[int] = None, message: str = "", limit: int = 3
    ) -> str:
        """Augment a prompt with RAG group context (multiple RAGs).

        Args:
            rag_group: The RAG group identifying which group of chatbots to use
            rag_type: Type of RAG - 'user_isolated' or 'chatbot_shared'
            user_id: The user ID (required if rag_type is 'user_isolated')
            message: The user message
            limit: Maximum number of chunks per RAG

        Returns:
            str: Augmented prompt with RAG context from all RAGs in the group
        """
        # Search for relevant documents from all RAGs in the group
        search_results = await self.search_rag_group(rag_group, rag_type, user_id, message, limit=limit)

        if not search_results:
            return message

        # Build context from top results, organized by RAG key
        context_by_rag = {}
        for result in search_results:
            rag_key = result["rag_key"]
            if rag_key not in context_by_rag:
                context_by_rag[rag_key] = []
            context_by_rag[rag_key].append(result["content"])

        # Create augmented prompt with organized context
        augmented_prompt = message + "\n\n📚 Context from knowledge base:\n"
        for rag_key, contents in context_by_rag.items():
            augmented_prompt += f"\n[{rag_key}]:\n"
            augmented_prompt += "\n".join(contents)
            augmented_prompt += "\n"

        return augmented_prompt


# Create singleton instance
rag_service = RAGService()
