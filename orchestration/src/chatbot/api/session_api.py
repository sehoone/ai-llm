"""Session management endpoints for the Chatbot API.

This module provides endpoints for creating, updating, deleting, and retrieving
chat sessions.
"""

import uuid
from typing import List

from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
)

from src.auth.api.auth_api import get_current_user
from src.auth.schemas.auth_schema import SessionResponse
from src.common.logging import logger
from src.common.services.database import database_service
from src.common.services.sanitization import sanitize_string
from src.user.models.user_model import User

router = APIRouter()

@router.post("/session", response_model=SessionResponse, summary="세션 생성", description="새로운 채팅 세션 생성")
async def create_session(user: User = Depends(get_current_user)):
    """Create a new chat session for the authenticated user.

    Args:
        user: The authenticated user

    Returns:
        SessionResponse: The session ID and name
    """
    try:
        # Generate a unique session ID
        session_id = str(uuid.uuid4())

        # Create session in database
        session = await database_service.create_session(session_id, user.id)

        logger.info(
            "session_created",
            session_id=session_id,
            user_id=user.id,
            name=session.name,
        )

        return SessionResponse(session_id=session_id, name=session.name)
    except ValueError as ve:
        logger.error("session_creation_validation_failed", error=str(ve), user_id=user.id, exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))


@router.patch(
    "/session/{session_id}/name",
    response_model=SessionResponse,
    summary="세션 이름 업데이트",
    description="세션의 이름을 업데이트합니다.",
)
async def update_session_name(
    session_id: str, name: str = Form(...), user: User = Depends(get_current_user)
):
    """Update a session's name.

    Args:
        session_id: The ID of the session to update
        name: The new name for the session
        user: The authenticated user

    Returns:
        SessionResponse: The updated session information
    """
    try:
        # Sanitize inputs
        sanitized_session_id = sanitize_string(session_id)
        sanitized_name = sanitize_string(name)

        # Verify session exists and belongs to user
        session = await database_service.get_session(sanitized_session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if session.user_id != user.id:
            raise HTTPException(status_code=403, detail="Cannot modify other sessions")

        # Update the session name
        session = await database_service.update_session_name(sanitized_session_id, sanitized_name)

        return SessionResponse(session_id=sanitized_session_id, name=session.name)
    except ValueError as ve:
        logger.error("session_update_validation_failed", error=str(ve), session_id=session_id, exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))


@router.delete("/session/{session_id}", summary="세션 삭제", description="인증된 사용자의 세션을 삭제합니다.")
async def delete_session(session_id: str, user: User = Depends(get_current_user)):
    """Delete a session for the authenticated user.

    Args:
        session_id: The ID of the session to delete
        user: The authenticated user

    Returns:
        None
    """
    try:
        # Sanitize inputs
        sanitized_session_id = sanitize_string(session_id)

        # Verify session exists and belongs to user
        session = await database_service.get_session(sanitized_session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
            
        if session.user_id != user.id:
            raise HTTPException(status_code=403, detail="Cannot delete other sessions")

        # Delete the session
        await database_service.delete_session(sanitized_session_id)

        logger.info("session_deleted", session_id=session_id, user_id=user.id)
    except ValueError as ve:
        logger.error("session_deletion_validation_failed", error=str(ve), session_id=session_id, exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))


@router.get(
    "/sessions",
    response_model=List[SessionResponse],
    summary="사용자 세션 목록 조회",
    description="인증된 사용자의 모든 세션을 조회합니다.",
)
async def get_user_sessions(user: User = Depends(get_current_user)):
    """Get all session IDs for the authenticated user.

    Args:
        user: The authenticated user

    Returns:
        List[SessionResponse]: List of session IDs
    """
    try:
        sessions = await database_service.get_user_sessions(user.id)
        return [
            SessionResponse(
                session_id=sanitize_string(session.id),
                name=sanitize_string(session.name),
            )
            for session in sessions
        ]
    except ValueError as ve:
        logger.error("get_sessions_validation_failed", user_id=user.id, error=str(ve), exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))
