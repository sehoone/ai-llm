"""Chatbot API endpoints for handling chat interactions.

This module provides endpoints for chat interactions, including regular chat,
streaming chat, message history management, and chat history clearing.
"""

import base64
import json
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import StreamingResponse

from src.auth.api.auth_api import get_current_user
from src.common.config import settings
from src.common.langgraph.graph import LangGraphAgent
from src.common.limiter import limiter
from src.common.logging import logger
from src.common.metrics import llm_stream_duration_seconds
from src.chatbot.models.session_model import Session
from src.user.models.user_model import User
from src.common.services.database import database_service
from src.chatbot.schemas.admin_schema import ChatHistoryResponse
from src.chatbot.schemas.chat_schema import (
    ALL_SUPPORTED_TYPES,
    ChatRequest,
    ChatResponse,
    FileAttachment,
    MAX_FILE_SIZE,
    Message,
    StreamResponse,
    SUPPORTED_IMAGE_TYPES,
    SUPPORTED_TEXT_TYPES,
)

router = APIRouter()
agent = LangGraphAgent()


@router.post("/chat", response_model=ChatResponse, summary="채팅 요청", description="LangGraph를 사용하여 채팅 요청을 처리합니다.")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["chat"][0])
async def chat(
    request: Request,
    chat_request: ChatRequest,
    user: User = Depends(get_current_user),
):
    """Process a chat request using LangGraph.

    Args:
        request: The FastAPI request object for rate limiting.
        chat_request: The chat request containing messages and session_id.
        user: The authenticated user.

    Returns:
        ChatResponse: The processed chat response.

    Raises:
        HTTPException: If there's an error processing the request.
    """
    try:
        # Verify session ownership
        session = await database_service.get_session(chat_request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if session.user_id != user.id:
            raise HTTPException(status_code=403, detail="Cannot access other sessions")

        logger.info(
            "chat_request_received",
            session_id=session.id,
            message_count=len(chat_request.messages),
        )

        result = await agent.get_response(
            chat_request.messages, 
            session.id, 
            user_id=session.user_id,
            is_deep_thinking=chat_request.is_deep_thinking
        )

        # Save interaction (user question + assistant answer)
        if chat_request.messages:
             last_user_msg = chat_request.messages[-1]
             if last_user_msg.role == "user":
                 # Find assistant response in result
                 # result is expected to be list of Message objects or dicts
                 # Assuming result contains the *new* messages from the agent execution
                 assistant_content = ""
                 for msg in result:
                     if msg.get("role") == "assistant":
                         assistant_content = msg.get("content", "")
                         break
                 
                 if assistant_content:
                     await database_service.save_chat_interaction(
                         session.id, 
                         last_user_msg.content, 
                         assistant_content
                     )

        logger.info("chat_request_processed", session_id=session.id)

        return ChatResponse(messages=result)
    except Exception as e:
        logger.error("chat_request_failed", session_id=chat_request.session_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/upload", response_model=ChatResponse, summary="파일 첨부 채팅 요청", description="LangGraph를 사용하여 파일 첨부 채팅 요청을 처리합니다.")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["chat"][0])
async def chat_with_files(
    request: Request,
    session_id: str = Form(..., description="The session ID"),
    message: str = Form(..., description="The user message"),
    is_deep_thinking: bool = Form(False, description="Whether to enable deep thinking mode"),
    files: Optional[List[UploadFile]] = File(default=None, description="Optional file attachments"),
    user: User = Depends(get_current_user),
):
    """Process a chat request with file attachments using LangGraph.

    Supports image files (JPEG, PNG, GIF, WebP) for vision analysis
    and text files (TXT, MD, CSV, JSON) for content extraction.

    Args:
        request: The FastAPI request object for rate limiting.
        session_id: The session ID.
        message: The user's text message.
        files: Optional list of file attachments.
        user: The authenticated user.

    Returns:
        ChatResponse: The processed chat response.

    Raises:
        HTTPException: If there's an error processing the request.
    """
    try:
        # Verify session ownership
        session = await database_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if session.user_id != user.id:
            raise HTTPException(status_code=403, detail="Cannot access other sessions")

        file_attachments = []
        
        if files:
            for file in files:
                # Validate file type
                if file.content_type not in ALL_SUPPORTED_TYPES:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unsupported file type: {file.content_type}. Supported: {ALL_SUPPORTED_TYPES}"
                    )
                
                # Read file content
                content = await file.read()
                
                # Validate file size
                if len(content) > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=400,
                        detail=f"File {file.filename} exceeds maximum size of {MAX_FILE_SIZE // (1024*1024)}MB"
                    )
                
                # Encode to base64
                encoded_content = base64.b64encode(content).decode("utf-8")
                
                file_attachments.append(FileAttachment(
                    filename=file.filename,
                    content_type=file.content_type,
                    data=encoded_content
                ))
        
        logger.info(
            "chat_with_files_request_received",
            session_id=session.id,
            file_count=len(file_attachments),
            file_types=[f.content_type for f in file_attachments] if file_attachments else [],
        )

        # Create message with file attachments
        user_message = Message(
            role="user",
            content=message,
            files=file_attachments if file_attachments else None
        )

        result = await agent.get_response(
            [user_message], 
            session.id, 
            user_id=session.user_id,
            is_deep_thinking=is_deep_thinking
        )

        logger.info("chat_with_files_request_processed", session_id=session.id)

        return ChatResponse(messages=result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("chat_with_files_request_failed", session_id=session.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream", response_model=None, summary="스트리밍 채팅 요청", description="LangGraph를 사용하여 스트리밍 채팅 요청을 처리합니다.")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["chat_stream"][0])
async def chat_stream(
    request: Request,
    chat_request: ChatRequest,
    user: User = Depends(get_current_user),
):
    """Process a chat request using LangGraph with streaming response.

    Args:
        request: The FastAPI request object for rate limiting.
        chat_request: The chat request containing messages and session_id.
        user: The authenticated user.

    Returns:
        StreamingResponse: A streaming response of the chat completion.

    Raises:
        HTTPException: If there's an error processing the request.
    """
    try:
        # Verify session ownership
        session = await database_service.get_session(chat_request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if session.user_id != user.id:
            raise HTTPException(status_code=403, detail="Cannot access other sessions")

        logger.info(
            "stream_chat_request_received",
            session_id=session.id,
            message_count=len(chat_request.messages),
        )

        async def event_generator():
            """Generate streaming events.

            Yields:
                str: Server-sent events in JSON format.

            Raises:
                Exception: If there's an error during streaming.
            """
            try:
                full_response = ""
                with llm_stream_duration_seconds.labels(model=agent.llm_service.get_llm().get_name()).time():
                    async for chunk in agent.get_stream_response(
                        chat_request.messages, 
                        session.id, 
                        user_id=session.user_id,
                        is_deep_thinking=chat_request.is_deep_thinking
                    ):
                        full_response += chunk
                        response = StreamResponse(content=chunk, done=False)
                        yield f"data: {json.dumps(response.model_dump(), ensure_ascii=False)}\n\n"

                # Save interaction (user question + full assistant answer)
                if chat_request.messages:
                    last_user_msg = chat_request.messages[-1]
                    if last_user_msg.role == "user" and full_response:
                         await database_service.save_chat_interaction(
                             session.id, 
                             last_user_msg.content, 
                             full_response
                         )

                # Send final message indicating completion
                final_response = StreamResponse(content="", done=True)
                yield f"data: {json.dumps(final_response.model_dump(), ensure_ascii=False)}\n\n"

            except Exception as e:
                logger.error(
                    "stream_chat_request_failed",
                    session_id=session.id,
                    error=str(e),
                    exc_info=True,
                )
                error_response = StreamResponse(content=str(e), done=True)
                yield f"data: {json.dumps(error_response.model_dump(), ensure_ascii=False)}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    except Exception as e:
        logger.error(
            "stream_chat_request_failed",
            session_id=chat_request.session_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/messages", response_model=ChatResponse, summary="세션 메시지 조회", description="인증된 사용자의 세션에 대한 모든 메시지를 조회합니다.")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["messages"][0])
async def get_session_messages(
    request: Request,
    session_id: str,
    user: User = Depends(get_current_user),
):
    """Get all messages for a session.

    Args:
        request: The FastAPI request object for rate limiting.
        session_id: The session ID.
        user: The authenticated user.

    Returns:
        ChatResponse: All messages in the session.

    Raises:
        HTTPException: If there's an error retrieving the messages.
    """
    try:
        # Verify session ownership
        session = await database_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if session.user_id != user.id:
            raise HTTPException(status_code=403, detail="Cannot access other sessions")

        # Get messages from DB
        db_messages = await database_service.get_chat_messages(session.id)
        
        # Convert Q/A pairs to flat list of messages
        messages = []
        for msg in db_messages:
            messages.append(Message(role="user", content=msg.question))
            messages.append(Message(role="assistant", content=msg.answer))
        
        return ChatResponse(messages=messages)
    except Exception as e:
        logger.error("get_messages_failed", session_id=session_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/messages", summary="세션 메시지 삭제", description="인증된 사용자의 세션에 대한 모든 메시지를 삭제합니다.")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["messages"][0])
async def clear_chat_history(
    request: Request,
    session_id: str,
    user: User = Depends(get_current_user),
):
    """Clear all messages for a session.

    Args:
        request: The FastAPI request object for rate limiting.
        session_id: The session ID.
        user: The authenticated user.

    Returns:
        dict: A message indicating the chat history was cleared.
    """
    try:
        # Verify session ownership
        session = await database_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if session.user_id != user.id:
            raise HTTPException(status_code=403, detail="Cannot access other sessions")

        await agent.clear_chat_history(session.id)
        return {"message": "Chat history cleared successfully"}
    except Exception as e:
        logger.error("clear_chat_history_failed", session_id=session_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/all", response_model=List[ChatHistoryResponse], summary="전체 대화 이력 조회", description="모든 사용자의 대화 이력을 조회합니다. (관리자용)")
async def get_all_chat_history(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    user: User = Depends(get_current_user),
):
    """Get all chat history for all users.

    Args:
        request: The FastAPI request object
        limit: Max records
        offset: Records to skip
        user: The authenticated user (Should be admin, but currently allowing any auth user for logic)

    Returns:
        List[ChatHistoryResponse]: List of chat histories
    """
    try:
        # TODO: Add admin check here
        history = await database_service.get_all_chat_history(limit=limit, offset=offset)
        return history
    except Exception as e:
        logger.error("get_all_chat_history_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{message_id}", response_model=ChatHistoryResponse, summary="대화 상세 조회", description="특정 대화 이력의 상세 정보를 조회합니다.")
async def get_chat_history_detail(
    message_id: int,
    user: User = Depends(get_current_user),
):
    """Get chat history detail by ID.

    Args:
        message_id: The ID of the chat message to retrieve
        user: The authenticated user

    Returns:
        ChatHistoryResponse: The chat history detail
    """
    try:
        # TODO: Add admin check here
        history = await database_service.get_chat_message_by_id(message_id)
        if not history:
            raise HTTPException(status_code=404, detail="Chat history not found")
        return history
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_chat_history_detail_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
