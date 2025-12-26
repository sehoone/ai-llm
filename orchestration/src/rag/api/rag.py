"""RAG API endpoints for document upload and semantic search."""

from typing import List

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)

from src.auth.api.auth import get_current_user
from src.common.config import settings
from src.common.limiter import limiter
from src.common.logging import logger
from src.user.models.user import User
from src.rag.schemas.rag import (
    DocumentResponse,
    RAGSearchResponse,
    RAGSearchResult,
)
from src.rag.services.document import document_service
from src.rag.services.rag import rag_service
from src.common.services.sanitization import sanitize_string

router = APIRouter()


@router.post("/upload", response_model=DocumentResponse, summary="문서 업로드", description="RAG를 위한 문서를 업로드합니다.")
@limiter.limit("10 per hour")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    rag_key: str = Form(...),
    rag_group: str = Form(...),
    rag_type: str = Form(...),
    tags: str = Form(default=""),
    user: User = Depends(get_current_user),
):
    """Upload a document for RAG.

    Args:
        request: The FastAPI request object for rate limiting.
        file: The file to upload
        rag_key: The RAG key identifying which chatbot/RAG this belongs to
        rag_group: The RAG group for batch searches (e.g., 'support_bots')
        rag_type: Type of RAG - 'user_isolated' (per-user) or 'chatbot_shared' (global)
        tags: Optional tags for the document
        user: The authenticated user

    Returns:
        DocumentResponse: The created document info

    Raises:
        HTTPException: If there's an error processing the request
    """
    try:
        logger.info("document_upload_received", filename=file.filename, user_id=user.id, rag_key=rag_key, rag_group=rag_group, rag_type=rag_type)
        
        # Validate rag_type
        if rag_type not in ["user_isolated", "chatbot_shared"]:
            raise HTTPException(status_code=400, detail="rag_type must be 'user_isolated' or 'chatbot_shared'")
        
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")

        # Check file size (max 10MB)
        MAX_FILE_SIZE = 10 * 1024 * 1024
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="File size exceeds 10MB limit")

        # Decode content
        try:
            file_content = content.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="File must be UTF-8 encoded text")

        # Sanitize inputs
        filename = sanitize_string(file.filename)
        doc_metadata = {
            "tags": sanitize_string(tags),
            "size": len(content),
        }

        logger.info("document_upload_started", filename=filename, user_id=user.id, rag_key=rag_key, rag_group=rag_group, rag_type=rag_type, size=len(content))

        # Create document
        doc = await document_service.create_document(
            rag_key=rag_key,
            rag_group=rag_group,
            rag_type=rag_type,
            filename=filename,
            content=file_content,
            user_id=user.id,  # Always save user_id
            doc_metadata=doc_metadata,
        )

        # Add to RAG
        success = await rag_service.add_document_to_rag(doc.id, rag_key, rag_group, rag_type, file_content)
        if not success:
            logger.warning("document_created_but_rag_failed", doc_id=doc.id, rag_type=rag_type, file_size=len(content))
            raise HTTPException(
                status_code=500,
                detail="Document created but failed to process for RAG. File may be too large or memory insufficient.",
            )

        logger.info("document_upload_completed", doc_id=doc.id, user_id=user.id, rag_type=rag_type)

        return DocumentResponse(
            id=doc.id,
            filename=doc.filename,
            user_id=doc.user_id,
            size=len(content),
            created_at=doc.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("document_upload_failed", error=str(e), user_id=user.id, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to upload document")


@router.get("/documents", response_model=List[DocumentResponse], summary="사용자 문서 목록 조회", description="인증된 사용자의 모든 문서를 조회합니다.")
@limiter.limit("30 per minute")
async def get_user_documents(
    request: Request,
    rag_key: str = None,
    rag_type: str = None,
    user: User = Depends(get_current_user),
):
    """Get all documents for the authenticated user.

    Args:
        request: The FastAPI request object for rate limiting.
        rag_key: Optional RAG key filter
        rag_type: Optional RAG type filter ('user_isolated' or 'chatbot_shared')
        user: The authenticated user

    Returns:
        List[DocumentResponse]: List of user's documents
    """
    try:
        docs = await document_service.get_user_documents(user.id, rag_key=rag_key, rag_type=rag_type)
        return [
            DocumentResponse(
                id=doc.id,
                filename=doc.filename,
                user_id=doc.user_id,
                size=len(doc.content),
                created_at=doc.created_at,
            )
            for doc in docs
        ]
    except Exception as e:
        logger.error("get_documents_failed", user_id=user.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve documents")


@router.delete("/documents/{doc_id}", summary="문서 삭제", description="인증된 사용자의 문서를 삭제합니다.")
@limiter.limit("30 per minute")
async def delete_document(
    request: Request,
    doc_id: int,
    user: User = Depends(get_current_user),
):
    """Delete a document.

    Args:
        request: The FastAPI request object for rate limiting.
        doc_id: The document ID to delete
        user: The authenticated user

    Returns:
        dict: Success message

    Raises:
        HTTPException: If document not found or unauthorized
    """
    try:
        # Verify document belongs to user
        doc = await document_service.get_document(doc_id)
        if not doc or doc.user_id != user.id:
            raise HTTPException(status_code=404, detail="Document not found")

        success = await document_service.delete_document(doc_id)
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")

        logger.info("document_deleted", doc_id=doc_id, user_id=user.id)
        return {"message": "Document deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_document_failed", doc_id=doc_id, user_id=user.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete document")


@router.post("/search", response_model=RAGSearchResponse, summary="RAG 문서 검색", description="RAG 문서들을 의미론적 유사도로 검색합니다.")
@limiter.limit("30 per minute")
async def search_rag(
    request: Request,
    rag_key: str = Form(...),
    rag_type: str = Form(...),
    query: str = Form(...),
    limit: int = Form(default=5),
    user: User = Depends(get_current_user),
):
    """Search RAG documents using semantic similarity.

    Args:
        request: The FastAPI request object for rate limiting.
        rag_key: The RAG key identifying which chatbot/RAG to search
        rag_type: Type of RAG - 'user_isolated' or 'chatbot_shared'
        query: The search query
        limit: Maximum number of results (default 5, max 20)
        user: The authenticated user

    Returns:
        RAGSearchResponse: Search results with similarity scores

    Raises:
        HTTPException: If there's an error processing the request
    """
    try:
        # Validate rag_type
        if rag_type not in ["user_isolated", "chatbot_shared"]:
            raise HTTPException(status_code=400, detail="rag_type must be 'user_isolated' or 'chatbot_shared'")
        
        # Validate inputs
        query = sanitize_string(query)
        if not query:
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        limit = min(max(1, limit), 20)  # Clamp between 1 and 20

        logger.info("rag_search_started", rag_key=rag_key, rag_type=rag_type, query=query, limit=limit, user_id=user.id)

        # Search RAG
        results = await rag_service.search_rag(
            rag_key=rag_key,
            rag_type=rag_type,
            user_id=user.id if rag_type == "user_isolated" else None,
            query=query,
            limit=limit
        )

        search_results = [
            RAGSearchResult(
                doc_id=result["doc_id"],
                filename=result["filename"],
                content=result["content"][:500],  # Truncate to 500 chars
                similarity=result["similarity"],
            )
            for result in results
        ]

        logger.info("rag_search_completed", user_id=user.id, results_count=len(search_results))

        return RAGSearchResponse(query=query, results=search_results)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("rag_search_failed", query=query, user_id=user.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to search documents")


@router.post("/search-group", response_model=RAGSearchResponse, summary="RAG 그룹 문서 검색", description="RAG 그룹에 속한 여러 RAG 문서들을 의미론적 유사도로 검색합니다.")
@limiter.limit("30 per minute")
async def search_rag_group(
    request: Request,
    rag_group: str = Form(...),
    rag_type: str = Form(...),
    query: str = Form(...),
    limit: int = Form(default=5),
    user: User = Depends(get_current_user),
):
    """Search multiple RAGs in a group using semantic similarity.

    Args:
        request: The FastAPI request object for rate limiting.
        rag_group: The RAG group containing multiple RAGs to search
        rag_type: Type of RAG - 'user_isolated' or 'chatbot_shared'
        query: The search query
        limit: Maximum number of results per RAG (default 5, max 20)
        user: The authenticated user

    Returns:
        RAGSearchResponse: Search results from all RAGs in the group with similarity scores

    Raises:
        HTTPException: If there's an error processing the request
    """
    try:
        # Validate rag_type
        if rag_type not in ["user_isolated", "chatbot_shared"]:
            raise HTTPException(status_code=400, detail="rag_type must be 'user_isolated' or 'chatbot_shared'")
        
        # Validate inputs
        query = sanitize_string(query)
        if not query:
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        limit = min(max(1, limit), 20)  # Clamp between 1 and 20

        logger.info("rag_group_search_started", rag_group=rag_group, rag_type=rag_type, query=query, limit=limit, user_id=user.id)

        # Search RAG Group
        results = await rag_service.search_rag_group(
            rag_group=rag_group,
            rag_type=rag_type,
            user_id=user.id if rag_type == "user_isolated" else None,
            query=query,
            limit=limit
        )

        search_results = [
            RAGSearchResult(
                doc_id=result["doc_id"],
                filename=result["filename"],
                content=result["content"][:500],  # Truncate to 500 chars
                similarity=result["similarity"],
            )
            for result in results
        ]

        logger.info("rag_group_search_completed", rag_group=rag_group, user_id=user.id, results_count=len(search_results))

        return RAGSearchResponse(query=query, results=search_results)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("rag_group_search_failed", rag_group=rag_group, query=query, user_id=user.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to search RAG group")
