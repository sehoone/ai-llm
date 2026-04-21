"""Agent management and chat endpoints."""

import json
from typing import List

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import StreamingResponse

from src.agent.models.agent_session_model import AgentSession
from src.agent.schemas.agent_schema import (
    AgentChatRequest,
    AgentCreate,
    AgentResponse,
    AgentSessionResponse,
    AgentUpdate,
    RagGroupInfo,
    RagKeyInfo,
)
from src.agent.services.agent_service import agent_service
from src.auth.api.auth_api import get_current_user
from src.chatbot.schemas.chat_schema import Message, StreamResponse
from src.chatbot.services.summary_service import chat_summary_service
from src.common.langgraph.graph import LangGraphAgent
from src.common.logging import logger
from src.common.services.database import database_service
from src.rag.services.rag_service import rag_service
from src.user.models.user_model import User

router = APIRouter()
_agent = LangGraphAgent()


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_owned_agent(agent_id: str, user: User):
    agent = await agent_service.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return agent


async def _get_owned_session(session_id: str, agent_id: str, user: User) -> AgentSession:
    session = await agent_service.get_session(session_id)
    if not session or session.agent_id != agent_id or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


async def _build_rag_context(agent, user_message: str, user_id: int) -> str:
    """Multi-key + multi-group RAG search and context injection."""
    if not agent.rag_enabled:
        return user_message
    if not agent.rag_keys and not agent.rag_groups:
        return user_message

    all_chunks: list[dict] = []

    for rag_key in (agent.rag_keys or []):
        results = await rag_service.search_rag(
            rag_key=rag_key,
            rag_type="chatbot_shared",
            user_id=user_id,
            query=user_message,
            limit=agent.rag_search_k,
        )
        all_chunks.extend(results)

    for rag_group in (agent.rag_groups or []):
        results = await rag_service.search_rag_group(
            rag_group=rag_group,
            rag_type="chatbot_shared",
            user_id=user_id,
            query=user_message,
            limit=agent.rag_search_k,
        )
        all_chunks.extend(results)

    if not all_chunks:
        return user_message

    all_chunks.sort(key=lambda x: x.get("similarity", 0), reverse=True)
    top_chunks = all_chunks[: agent.rag_search_k]

    context = "\n\n".join(c["content"] for c in top_chunks)
    return f"{user_message}\n\nContext from knowledge base:\n{context}"


# ── Agent CRUD ────────────────────────────────────────────────────────────────

@router.get("/rag-keys", response_model=List[RagKeyInfo], summary="사용 가능한 RAG 키 목록")
async def list_rag_keys(user: User = Depends(get_current_user)):
    return await agent_service.list_rag_keys(user.id)


@router.get("/rag-groups", response_model=List[RagGroupInfo], summary="사용 가능한 RAG 그룹 목록")
async def list_rag_groups(user: User = Depends(get_current_user)):
    return await agent_service.list_rag_groups(user.id)


@router.get("/", response_model=List[AgentResponse], summary="에이전트 목록")
async def list_agents(user: User = Depends(get_current_user)):
    return await agent_service.list_agents(user.id)


@router.post("/", response_model=AgentResponse, summary="에이전트 생성")
async def create_agent(data: AgentCreate, user: User = Depends(get_current_user)):
    return await agent_service.create_agent(data, user.id)


@router.get("/{agent_id}", response_model=AgentResponse, summary="에이전트 상세")
async def get_agent(agent_id: str, user: User = Depends(get_current_user)):
    return await _get_owned_agent(agent_id, user)


@router.put("/{agent_id}", response_model=AgentResponse, summary="에이전트 수정")
async def update_agent(agent_id: str, data: AgentUpdate, user: User = Depends(get_current_user)):
    await _get_owned_agent(agent_id, user)
    agent = await agent_service.update_agent(agent_id, data, user.id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.delete("/{agent_id}", summary="에이전트 삭제")
async def delete_agent(agent_id: str, user: User = Depends(get_current_user)):
    await _get_owned_agent(agent_id, user)
    await agent_service.delete_agent(agent_id, user.id)
    return {"message": "Agent deleted successfully"}


@router.post("/{agent_id}/publish", response_model=AgentResponse, summary="게시 토글")
async def toggle_publish(agent_id: str, user: User = Depends(get_current_user)):
    await _get_owned_agent(agent_id, user)
    agent = await agent_service.toggle_publish(agent_id, user.id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


# ── Session management ────────────────────────────────────────────────────────

@router.post("/{agent_id}/sessions", response_model=AgentSessionResponse, summary="세션 생성")
async def create_session(agent_id: str, user: User = Depends(get_current_user)):
    await _get_owned_agent(agent_id, user)
    session = await agent_service.create_session(agent_id, user.id)
    return AgentSessionResponse(session_id=session.id, agent_id=session.agent_id, name=session.name, created_at=session.created_at)


@router.get("/{agent_id}/sessions", response_model=List[AgentSessionResponse], summary="세션 목록")
async def list_sessions(agent_id: str, user: User = Depends(get_current_user)):
    await _get_owned_agent(agent_id, user)
    sessions = await agent_service.list_sessions(agent_id, user.id)
    return [AgentSessionResponse(session_id=s.id, agent_id=s.agent_id, name=s.name, created_at=s.created_at) for s in sessions]


@router.patch("/{agent_id}/sessions/{session_id}/name", response_model=AgentSessionResponse, summary="세션 이름 변경")
async def rename_session(
    agent_id: str,
    session_id: str,
    name: str = Form(...),
    user: User = Depends(get_current_user),
):
    await _get_owned_session(session_id, agent_id, user)
    session = await agent_service.rename_session(session_id, name)
    return AgentSessionResponse(session_id=session.id, agent_id=session.agent_id, name=session.name, created_at=session.created_at)


@router.delete("/{agent_id}/sessions/{session_id}", summary="세션 삭제")
async def delete_session(agent_id: str, session_id: str, user: User = Depends(get_current_user)):
    await _get_owned_session(session_id, agent_id, user)
    await _agent.clear_chat_history(session_id)
    await agent_service.delete_session(session_id)
    return {"message": "Session deleted successfully"}


# ── Chat ──────────────────────────────────────────────────────────────────────

@router.get("/{agent_id}/messages", summary="세션 메시지 조회")
async def get_messages(agent_id: str, session_id: str, user: User = Depends(get_current_user)):
    await _get_owned_session(session_id, agent_id, user)
    db_messages = await database_service.get_gpt_chat_messages(session_id)
    messages = []
    for msg in db_messages:
        messages.append(Message(role="user", content=msg.question))
        messages.append(Message(role="assistant", content=msg.answer))
    return {"messages": messages}


@router.post("/{agent_id}/chat/stream", summary="에이전트 스트리밍 채팅")
async def chat_stream(
    agent_id: str,
    chat_request: AgentChatRequest,
    user: User = Depends(get_current_user),
):
    agent = await _get_owned_agent(agent_id, user)
    session = await _get_owned_session(chat_request.session_id, agent_id, user)

    logger.info("agent_stream_chat", agent_id=agent_id, session_id=session.id)

    async def event_generator():
        try:
            full_response = ""

            last_user_content = chat_request.messages[-1].content if chat_request.messages else ""
            augmented_content = await _build_rag_context(agent, last_user_content, user.id)

            augmented_messages = list(chat_request.messages)
            if augmented_content != last_user_content:
                augmented_messages = augmented_messages[:-1] + [
                    Message(role="user", content=augmented_content)
                ]

            async for chunk in _agent.get_stream_response(
                augmented_messages,
                session.id,
                user_id=session.user_id,
                is_deep_thinking=chat_request.is_deep_thinking,
                system_instructions=agent.system_prompt,
                rag_key=None,
                model_name=agent.model,
            ):
                full_response += chunk
                yield f"data: {json.dumps(StreamResponse(content=chunk, done=False).model_dump(), ensure_ascii=False)}\n\n"

            if chat_request.messages and full_response:
                last_user_msg = chat_request.messages[-1]
                if last_user_msg.role == "user":
                    existing = await database_service.get_gpt_chat_messages(session.id)
                    is_first = len(existing) == 0
                    await database_service.save_gpt_chat_interaction(session.id, last_user_msg.content, full_response)

                    if is_first:
                        try:
                            new_title = await chat_summary_service.generate_title(last_user_msg.content, full_response)
                            await agent_service.rename_session(session.id, new_title)
                            title_event = StreamResponse(content="", done=False, type="title", title=new_title)
                            yield f"data: {json.dumps(title_event.model_dump(), ensure_ascii=False)}\n\n"
                        except Exception as e:
                            logger.error("agent_title_generation_failed", error=str(e))

            yield f"data: {json.dumps(StreamResponse(content='', done=True).model_dump(), ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error("agent_stream_failed", agent_id=agent_id, session_id=session.id, error=str(e), exc_info=True)
            yield f"data: {json.dumps(StreamResponse(content=str(e), done=True).model_dump(), ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
