import json
import uuid
from typing import List

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import StreamingResponse

from src.auth.api.auth_api import get_current_user
from src.chatbot.deps import get_owned_gpt_session
from src.chatbot.schemas.chat_schema import ChatResponse, Message, StreamResponse
from src.chatbot.schemas.custom_gpt_schema import (
    CustomGPTCreate,
    CustomGPTResponse,
    CustomGPTUpdate,
    GPTChatRequest,
    GPTSessionResponse,
)
from src.chatbot.services.custom_gpt_service import custom_gpt_service
from src.chatbot.services.summary_service import chat_summary_service
from src.common.langgraph.graph import LangGraphAgent
from src.common.logging import logger
from src.common.services.database import database_service
from src.user.models.user_model import User

router = APIRouter()
agent = LangGraphAgent()


# ── CustomGPT CRUD ────────────────────────────────────────────────────────────

@router.post("/", response_model=CustomGPTResponse, summary="Create a new Custom GPT")
async def create_custom_gpt(
    gpt_create: CustomGPTCreate,
    user: User = Depends(get_current_user),
):
    return await custom_gpt_service.create_gpt(gpt_create, user.id)


@router.get("/", response_model=List[CustomGPTResponse], summary="List all Custom GPTs for the user")
async def list_custom_gpts(
    user: User = Depends(get_current_user),
):
    return await custom_gpt_service.list_gpts(user.id)


@router.get("/{gpt_id}", response_model=CustomGPTResponse, summary="Get a specific Custom GPT")
async def get_custom_gpt(
    gpt_id: str,
    user: User = Depends(get_current_user),
):
    gpt = await custom_gpt_service.get_gpt(gpt_id)
    if not gpt:
        raise HTTPException(status_code=404, detail="Custom GPT not found")
    if not gpt.is_public and gpt.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return gpt


@router.put("/{gpt_id}", response_model=CustomGPTResponse, summary="Update a Custom GPT")
async def update_custom_gpt(
    gpt_id: str,
    gpt_update: CustomGPTUpdate,
    user: User = Depends(get_current_user),
):
    gpt = await custom_gpt_service.update_gpt(gpt_id, gpt_update, user.id)
    if not gpt:
        raise HTTPException(status_code=404, detail="Custom GPT not found or access denied")
    return gpt


@router.delete("/{gpt_id}", summary="Delete a Custom GPT")
async def delete_custom_gpt(
    gpt_id: str,
    user: User = Depends(get_current_user),
):
    success = await custom_gpt_service.delete_gpt(gpt_id, user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Custom GPT not found or access denied")
    return {"message": "Custom GPT deleted successfully"}


# ── GPT Session management ────────────────────────────────────────────────────

@router.post("/{gpt_id}/sessions", response_model=GPTSessionResponse, summary="GPT 세션 생성")
async def create_gpt_session(
    gpt_id: str,
    user: User = Depends(get_current_user),
):
    gpt = await custom_gpt_service.get_gpt(gpt_id)
    if not gpt:
        raise HTTPException(status_code=404, detail="Custom GPT not found")
    if not gpt.is_public and gpt.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    session_id = str(uuid.uuid4())
    session = await database_service.create_gpt_session(session_id, user.id, gpt_id)
    return GPTSessionResponse(session_id=session.id, name=session.name, custom_gpt_id=session.custom_gpt_id)


@router.get("/{gpt_id}/sessions", response_model=List[GPTSessionResponse], summary="GPT 세션 목록 조회")
async def list_gpt_sessions(
    gpt_id: str,
    user: User = Depends(get_current_user),
):
    gpt = await custom_gpt_service.get_gpt(gpt_id)
    if not gpt:
        raise HTTPException(status_code=404, detail="Custom GPT not found")
    if not gpt.is_public and gpt.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    sessions = await database_service.get_user_gpt_sessions(user.id, gpt_id)
    return [GPTSessionResponse(session_id=s.id, name=s.name, custom_gpt_id=s.custom_gpt_id) for s in sessions]


@router.patch("/{gpt_id}/sessions/{session_id}/name", response_model=GPTSessionResponse, summary="GPT 세션 이름 변경")
async def rename_gpt_session(
    gpt_id: str,
    session_id: str,
    name: str = Form(...),
    user: User = Depends(get_current_user),
):
    session = await get_owned_gpt_session(session_id, gpt_id, user)

    updated = await database_service.update_gpt_session_name(session_id, name)
    return GPTSessionResponse(session_id=updated.id, name=updated.name, custom_gpt_id=updated.custom_gpt_id)


@router.delete("/{gpt_id}/sessions/{session_id}", summary="GPT 세션 삭제")
async def delete_gpt_session(
    gpt_id: str,
    session_id: str,
    user: User = Depends(get_current_user),
):
    session = await get_owned_gpt_session(session_id, gpt_id, user)

    await agent.clear_chat_history(session_id)
    await database_service.delete_gpt_session(session_id)
    return {"message": "Session deleted successfully"}


# ── GPT Chat ──────────────────────────────────────────────────────────────────

@router.post("/{gpt_id}/chat", response_model=ChatResponse, summary="GPT 채팅 (non-streaming)")
async def gpt_chat(
    gpt_id: str,
    chat_request: GPTChatRequest,
    user: User = Depends(get_current_user),
):
    gpt = await custom_gpt_service.get_gpt(gpt_id)
    if not gpt:
        raise HTTPException(status_code=404, detail="Custom GPT not found")
    if not gpt.is_public and gpt.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    session = await get_owned_gpt_session(chat_request.session_id, gpt_id, user)

    logger.info("gpt_chat_request", gpt_id=gpt_id, session_id=session.id)

    try:
        result = await agent.get_response(
            chat_request.messages,
            session.id,
            user_id=session.user_id,
            is_deep_thinking=chat_request.is_deep_thinking,
            system_instructions=gpt.instructions,
            rag_key=gpt.rag_key,
        )

        if chat_request.messages:
            last_user_msg = chat_request.messages[-1]
            if last_user_msg.role == "user":
                assistant_content = ""
                for msg in result:
                    if msg.get("role") == "assistant":
                        assistant_content = msg.get("content", "")
                        break
                if assistant_content:
                    await database_service.save_gpt_chat_interaction(session.id, last_user_msg.content, assistant_content)

        return ChatResponse(messages=result)
    except Exception as e:
        logger.error("gpt_chat_failed", gpt_id=gpt_id, session_id=session.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{gpt_id}/chat/stream", response_model=None, summary="GPT 스트리밍 채팅")
async def gpt_chat_stream(
    gpt_id: str,
    chat_request: GPTChatRequest,
    user: User = Depends(get_current_user),
):
    gpt = await custom_gpt_service.get_gpt(gpt_id)
    if not gpt:
        raise HTTPException(status_code=404, detail="Custom GPT not found")
    if not gpt.is_public and gpt.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    session = await get_owned_gpt_session(chat_request.session_id, gpt_id, user)

    logger.info("gpt_stream_chat_request", gpt_id=gpt_id, session_id=session.id)

    async def event_generator():
        try:
            full_response = ""
            async for chunk in agent.get_stream_response(
                chat_request.messages,
                session.id,
                user_id=session.user_id,
                is_deep_thinking=chat_request.is_deep_thinking,
                system_instructions=gpt.instructions,
                rag_key=gpt.rag_key,
            ):
                full_response += chunk
                response = StreamResponse(content=chunk, done=False)
                yield f"data: {json.dumps(response.model_dump(), ensure_ascii=False)}\n\n"

            if chat_request.messages:
                last_user_msg = chat_request.messages[-1]
                if last_user_msg.role == "user" and full_response:
                    existing = await database_service.get_gpt_chat_messages(session.id)
                    is_first = len(existing) == 0

                    await database_service.save_gpt_chat_interaction(session.id, last_user_msg.content, full_response)

                    if is_first:
                        try:
                            new_title = await chat_summary_service.generate_title(last_user_msg.content, full_response)
                            await database_service.update_gpt_session_name(session.id, new_title)
                            logger.info("gpt_session_title_updated", session_id=session.id, title=new_title)
                            title_event = StreamResponse(content="", done=False, type="title", title=new_title)
                            yield f"data: {json.dumps(title_event.model_dump(), ensure_ascii=False)}\n\n"
                        except Exception as e:
                            logger.error("gpt_title_generation_failed", error=str(e))

            final = StreamResponse(content="", done=True)
            yield f"data: {json.dumps(final.model_dump(), ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error("gpt_stream_chat_failed", gpt_id=gpt_id, session_id=session.id, error=str(e), exc_info=True)
            error_response = StreamResponse(content=str(e), done=True)
            yield f"data: {json.dumps(error_response.model_dump(), ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ── GPT Message history ───────────────────────────────────────────────────────

@router.get("/{gpt_id}/messages", response_model=ChatResponse, summary="GPT 세션 메시지 조회")
async def get_gpt_messages(
    gpt_id: str,
    session_id: str,
    user: User = Depends(get_current_user),
):
    session = await get_owned_gpt_session(session_id, gpt_id, user)

    db_messages = await database_service.get_gpt_chat_messages(session.id)
    messages = []
    for msg in db_messages:
        messages.append(Message(role="user", content=msg.question))
        messages.append(Message(role="assistant", content=msg.answer))
    return ChatResponse(messages=messages)


@router.delete("/{gpt_id}/messages", summary="GPT 세션 메시지 삭제")
async def clear_gpt_messages(
    gpt_id: str,
    session_id: str,
    user: User = Depends(get_current_user),
):
    session = await get_owned_gpt_session(session_id, gpt_id, user)

    await agent.clear_chat_history(session.id)
    await database_service.delete_gpt_chat_messages(session.id)
    return {"message": "Chat history cleared successfully"}
