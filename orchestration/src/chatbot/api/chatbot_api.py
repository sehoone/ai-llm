"""Chatbot API endpoints for handling chat interactions.

This module provides endpoints for chat interactions, including regular chat,
streaming chat, message history management, and chat history clearing.
"""

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
from fastapi.responses import FileResponse, StreamingResponse

from src.auth.api.auth_api import get_current_user, require_admin
from src.user.models.user_model import UserRole
from src.chatbot.deps import get_owned_chat_session
from src.chatbot.services.file_storage_service import FileStorageService
from src.common.config import settings
from src.common.langgraph.graph import LangGraphAgent
from src.common.limiter import limiter
from src.common.logging import logger
from src.common.metrics import llm_stream_duration_seconds
from src.user.models.user_model import User
from src.common.services.database import database_service
from src.chatbot.schemas.admin_schema import ChatHistoryResponse, ChatHistoryListResponse
from src.chatbot.schemas.chat_schema import (
    ALL_SUPPORTED_TYPES,
    AttachmentMeta,
    ChatRequest,
    ChatResponse,
    FileAttachment,
    MAX_FILE_SIZE,
    Message,
    StreamResponse,
)
from src.chatbot.services.summary_service import chat_summary_service

router = APIRouter()
agent = LangGraphAgent()
file_storage = FileStorageService(settings.UPLOAD_DIR)


@router.post("/chat", response_model=ChatResponse, summary="채팅 요청", description="LangGraph를 사용하여 채팅 요청을 처리합니다.")
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
        session = await get_owned_chat_session(chat_request.session_id, user)

        logger.info(
            "chat_request_received",
            session_id=session.id,
            message_count=len(chat_request.messages),
        )

        result = await agent.get_response(
            chat_request.messages,
            session.id,
            user_id=session.user_id,
            is_deep_thinking=chat_request.is_deep_thinking,
        )

        if chat_request.messages:
            last_user_msg = chat_request.messages[-1]
            if last_user_msg.role == "user":
                assistant_content = next((m.content for m in result if m.role == "assistant"), "")
                if assistant_content:
                    await database_service.save_chat_interaction(
                        session.id,
                        last_user_msg.content,
                        assistant_content,
                    )

        logger.info("chat_request_processed", session_id=session.id)
        return ChatResponse(messages=result)
    except Exception as e:
        logger.error("chat_request_failed", session_id=chat_request.session_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/upload", response_model=ChatResponse, summary="파일 첨부 채팅 요청", description="LangGraph를 사용하여 파일 첨부 채팅 요청을 처리합니다.")
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
        is_deep_thinking: Whether to enable deep thinking mode.
        files: Optional list of file attachments.
        user: The authenticated user.

    Returns:
        ChatResponse: The processed chat response.

    Raises:
        HTTPException: If there's an error processing the request.
    """
    try:
        session = await get_owned_chat_session(session_id, user)

        file_attachments: List[FileAttachment] = []
        if files:
            for file in files:
                if file.content_type not in ALL_SUPPORTED_TYPES:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unsupported file type: {file.content_type}",
                    )
                content = await file.read()
                if len(content) > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=400,
                        detail=f"File {file.filename} exceeds maximum size of {MAX_FILE_SIZE // (1024*1024)}MB",
                    )
                import base64
                file_attachments.append(FileAttachment(
                    filename=file.filename,
                    content_type=file.content_type,
                    data=base64.b64encode(content).decode("utf-8"),
                ))

        user_message = Message(
            role="user",
            content=message,
            files=file_attachments if file_attachments else None,
        )

        result = await agent.get_response(
            [user_message],
            session.id,
            user_id=session.user_id,
            is_deep_thinking=is_deep_thinking,
        )

        assistant_content = next((m.content for m in result if m.role == "assistant"), "")
        if assistant_content:
            saved_msg = await database_service.save_chat_interaction(
                session.id, message, assistant_content
            )
            for fa in file_attachments:
                storage_path, file_size = await file_storage.save(fa.data, session.id, fa.filename)
                await database_service.create_attachment(
                    message_id=saved_msg.id,
                    session_id=session.id,
                    filename=fa.filename,
                    content_type=fa.content_type,
                    file_size=file_size,
                    storage_path=storage_path,
                )

        logger.info("chat_with_files_request_processed", session_id=session.id)
        return ChatResponse(messages=result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("chat_with_files_request_failed", session_id=session_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream", response_model=None, summary="스트리밍 채팅 요청", description="LangGraph를 사용하여 스트리밍 채팅 요청을 처리합니다.")
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
        session = await get_owned_chat_session(chat_request.session_id, user)

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
                        is_deep_thinking=chat_request.is_deep_thinking,
                    ):
                        full_response += chunk
                        response = StreamResponse(content=chunk, done=False)
                        yield f"data: {json.dumps(response.model_dump(), ensure_ascii=False)}\n\n"

                if chat_request.messages:
                    last_user_msg = chat_request.messages[-1]
                    if last_user_msg.role == "user" and full_response:
                        existing_history = await database_service.get_chat_messages(session.id)
                        is_first_interaction = len(existing_history) == 0

                        saved_msg = await database_service.save_chat_interaction(
                            session.id,
                            last_user_msg.content,
                            full_response,
                            is_deep_thinking=chat_request.is_deep_thinking,
                        )

                        # Persist file attachments linked to the saved message
                        if last_user_msg.files:
                            for fa in last_user_msg.files:
                                try:
                                    storage_path, file_size = await file_storage.save(
                                        fa.data, session.id, fa.filename
                                    )
                                    await database_service.create_attachment(
                                        message_id=saved_msg.id,
                                        session_id=session.id,
                                        filename=fa.filename,
                                        content_type=fa.content_type,
                                        file_size=file_size,
                                        storage_path=storage_path,
                                    )
                                except Exception as e:
                                    logger.error("attachment_save_failed", filename=fa.filename, error=str(e))

                        if is_first_interaction:
                            try:
                                new_title = await chat_summary_service.generate_title(last_user_msg.content, full_response)
                                await database_service.update_session_name(session.id, new_title)
                                logger.info("session_title_updated", session_id=session.id, title=new_title)

                                title_event = StreamResponse(content="", done=False, type="title", title=new_title)
                                yield f"data: {json.dumps(title_event.model_dump(), ensure_ascii=False)}\n\n"
                            except Exception as e:
                                logger.error("title_generation_failed", error=str(e))

                final_response = StreamResponse(content="", done=True)
                yield f"data: {json.dumps(final_response.model_dump(), ensure_ascii=False)}\n\n"

            except Exception as e:
                logger.error("stream_chat_request_failed", session_id=session.id, error=str(e), exc_info=True)
                error_response = StreamResponse(content=str(e), done=True)
                yield f"data: {json.dumps(error_response.model_dump(), ensure_ascii=False)}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    except Exception as e:
        logger.error("stream_chat_request_failed", session_id=chat_request.session_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/messages", response_model=ChatResponse, summary="세션 메시지 조회", description="인증된 사용자의 세션에 대한 모든 메시지를 조회합니다.")
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
        session = await get_owned_chat_session(session_id, user)

        db_messages = await database_service.get_chat_messages(session.id)

        # Batch-fetch attachments for all messages (avoids N+1)
        message_ids = [m.id for m in db_messages if m.id is not None]
        attachments_by_msg = await database_service.get_attachments_by_message_ids(message_ids) if message_ids else {}

        messages: List[Message] = []
        for msg in db_messages:
            raw_attachments = attachments_by_msg.get(msg.id, [])
            attachment_meta = [
                AttachmentMeta(
                    id=a.id,
                    filename=a.filename,
                    content_type=a.content_type,
                    file_size=a.file_size,
                )
                for a in raw_attachments
            ] or None
            messages.append(Message(role="user", content=msg.question, attachments=attachment_meta))
            messages.append(Message(role="assistant", content=msg.answer))

        return ChatResponse(messages=messages)
    except Exception as e:
        logger.error("get_messages_failed", session_id=session_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/messages", summary="세션 메시지 삭제", description="인증된 사용자의 세션에 대한 모든 메시지를 삭제합니다.")
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
        session = await get_owned_chat_session(session_id, user)
        await agent.clear_chat_history(session.id)
        await database_service.delete_chat_messages(session.id)
        return {"message": "Chat history cleared successfully"}
    except Exception as e:
        logger.error("clear_chat_history_failed", session_id=session_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/attachments/{attachment_id}", summary="첨부파일 다운로드", description="인증된 사용자가 본인 세션의 첨부파일을 다운로드합니다.")
async def download_attachment(
    attachment_id: int,
    user: User = Depends(get_current_user),
):
    """Download a file attachment.

    Regular users can only download attachments from their own sessions.
    Admins and superadmins can download any attachment.

    Args:
        attachment_id: The attachment ID to download.
        user: The authenticated user.

    Returns:
        FileResponse: The file stream with appropriate content-type header.

    Raises:
        HTTPException: 404 if not found, 403 if access denied.
    """
    attachment = await database_service.get_attachment(attachment_id)
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    # Admins can download any attachment; regular users only their own
    is_admin = user.role in (UserRole.ADMIN, UserRole.SUPERADMIN)
    if not is_admin:
        session = await database_service.get_session(attachment.session_id)
        if not session or session.user_id != user.id:
            raise HTTPException(status_code=403, detail="Access denied")

    file_path = file_storage.absolute_path(attachment.storage_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on server")

    return FileResponse(
        path=str(file_path),
        filename=attachment.filename,
        media_type=attachment.content_type,
    )


@router.get("/history/all", response_model=ChatHistoryListResponse, summary="전체 대화 이력 조회", description="모든 사용자의 대화 이력을 조회합니다. (관리자용)")
async def get_all_chat_history(
    request: Request,
    limit: int = 20,
    offset: int = 0,
    search: str = "",
    user: User = Depends(require_admin),
):
    """Get all chat history for all users with server-side pagination and search.

    Args:
        request: The FastAPI request object.
        limit: Max records to return.
        offset: Records to skip.
        search: Keyword to filter across question, answer, user email, and session name.
        user: The authenticated admin user.

    Returns:
        ChatHistoryListResponse: Paginated chat histories with total count.
    """
    try:
        result = await database_service.get_all_chat_history(limit=limit, offset=offset, search=search)

        message_ids = [h["id"] for h in result["items"]]
        attachments_by_msg = await database_service.get_attachments_by_message_ids(message_ids) if message_ids else {}

        return ChatHistoryListResponse(
            items=[
                ChatHistoryResponse(
                    **h,
                    attachments=[
                        AttachmentMeta(id=a.id, filename=a.filename, content_type=a.content_type, file_size=a.file_size)
                        for a in attachments_by_msg.get(h["id"], [])
                    ],
                )
                for h in result["items"]
            ],
            total=result["total"],
        )
    except Exception as e:
        logger.error("get_all_chat_history_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{message_id}", response_model=ChatHistoryResponse, summary="대화 상세 조회", description="특정 대화 이력의 상세 정보를 조회합니다.")
async def get_chat_history_detail(
    message_id: int,
    user: User = Depends(require_admin),
):
    """Get chat history detail by ID.

    Args:
        message_id: The ID of the chat message to retrieve.
        user: The authenticated admin user.

    Returns:
        ChatHistoryResponse: The chat history detail with attachment metadata.
    """
    try:
        history = await database_service.get_chat_message_by_id(message_id)
        if not history:
            raise HTTPException(status_code=404, detail="Chat history not found")

        attachments_by_msg = await database_service.get_attachments_by_message_ids([history["id"]])
        return ChatHistoryResponse(
            **history,
            attachments=[
                AttachmentMeta(id=a.id, filename=a.filename, content_type=a.content_type, file_size=a.file_size)
                for a in attachments_by_msg.get(history["id"], [])
            ],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_chat_history_detail_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
