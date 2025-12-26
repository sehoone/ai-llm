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

from src.auth.api.auth import get_current_session
from src.common.config import settings
from src.common.langgraph.graph import LangGraphAgent
from src.common.limiter import limiter
from src.common.logging import logger
from src.common.metrics import llm_stream_duration_seconds
from src.chatbot.models.session import Session
from src.chatbot.schemas.chat import (
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
    session: Session = Depends(get_current_session),
):
    """Process a chat request using LangGraph.

    Args:
        request: The FastAPI request object for rate limiting.
        chat_request: The chat request containing messages.
        session: The current session from the auth token.

    Returns:
        ChatResponse: The processed chat response.

    Raises:
        HTTPException: If there's an error processing the request.
    """
    try:
        logger.info(
            "chat_request_received",
            session_id=session.id,
            message_count=len(chat_request.messages),
        )

        result = await agent.get_response(chat_request.messages, session.id, user_id=session.user_id)

        logger.info("chat_request_processed", session_id=session.id)

        return ChatResponse(messages=result)
    except Exception as e:
        logger.error("chat_request_failed", session_id=session.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/upload", response_model=ChatResponse, summary="파일 첨부 채팅 요청", description="LangGraph를 사용하여 파일 첨부 채팅 요청을 처리합니다.")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["chat"][0])
async def chat_with_files(
    request: Request,
    message: str = Form(..., description="The user message"),
    files: Optional[List[UploadFile]] = File(default=None, description="Optional file attachments"),
    session: Session = Depends(get_current_session),
):
    """Process a chat request with file attachments using LangGraph.

    Supports image files (JPEG, PNG, GIF, WebP) for vision analysis
    and text files (TXT, MD, CSV, JSON) for content extraction.

    Args:
        request: The FastAPI request object for rate limiting.
        message: The user's text message.
        files: Optional list of file attachments.
        session: The current session from the auth token.

    Returns:
        ChatResponse: The processed chat response.

    Raises:
        HTTPException: If there's an error processing the request.
    """
    try:
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

        result = await agent.get_response([user_message], session.id, user_id=session.user_id)

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
    session: Session = Depends(get_current_session),
):
    """Process a chat request using LangGraph with streaming response.

    Args:
        request: The FastAPI request object for rate limiting.
        chat_request: The chat request containing messages.
        session: The current session from the auth token.

    Returns:
        StreamingResponse: A streaming response of the chat completion.

    Raises:
        HTTPException: If there's an error processing the request.
    """
    try:
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
                        chat_request.messages, session.id, user_id=session.user_id
                    ):
                        full_response += chunk
                        response = StreamResponse(content=chunk, done=False)
                        yield f"data: {json.dumps(response.model_dump(), ensure_ascii=False)}\n\n"

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
            session_id=session.id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/messages", response_model=ChatResponse, summary="세션 메시지 조회", description="인증된 사용자의 세션에 대한 모든 메시지를 조회합니다.")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["messages"][0])
async def get_session_messages(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Get all messages for a session.

    Args:
        request: The FastAPI request object for rate limiting.
        session: The current session from the auth token.

    Returns:
        ChatResponse: All messages in the session.

    Raises:
        HTTPException: If there's an error retrieving the messages.
    """
    try:
        messages = await agent.get_chat_history(session.id)
        return ChatResponse(messages=messages)
    except Exception as e:
        logger.error("get_messages_failed", session_id=session.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/messages", summary="세션 메시지 삭제", description="인증된 사용자의 세션에 대한 모든 메시지를 삭제합니다.")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["messages"][0])
async def clear_chat_history(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Clear all messages for a session.

    Args:
        request: The FastAPI request object for rate limiting.
        session: The current session from the auth token.

    Returns:
        dict: A message indicating the chat history was cleared.
    """
    try:
        await agent.clear_chat_history(session.id)
        return {"message": "Chat history cleared successfully"}
    except Exception as e:
        logger.error("clear_chat_history_failed", session_id=session.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
