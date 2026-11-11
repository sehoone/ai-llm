"""gpts 도메인 라우터 — 커스텀 GPT CRUD·세션·메시지·채팅(SSE).

경로는 web(V2 기준) 계약을 유지한다(`/api/v1/gpts/...`). 비스트림 응답은 `ApiResponse[T]`로
감싸고(web axios 인터셉터가 자동 unwrap), 채팅은 text/event-stream.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from src.core.db import get_session
from src.core.response import ApiResponse
from src.platform.auth.dependencies import get_current_user
from src.domains.gpts.schema import (
    CustomGptCreateRequest,
    CustomGptResponse,
    CustomGptUpdateRequest,
    GptChatHistoryResponse,
    GptChatRequest,
    GptSessionResponse,
    SessionRenameRequest,
)
from src.domains.gpts.service import GptsService
from src.platform.user.model import User

router = APIRouter()

_SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


# ── CustomGPT CRUD ──
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[CustomGptResponse])
def create_gpt(
    req: CustomGptCreateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[CustomGptResponse]:
    g = GptsService(session).create_gpt(user, req)
    return ApiResponse.ok(CustomGptResponse.from_model(g))


@router.get("/", response_model=ApiResponse[list[CustomGptResponse]])
def list_gpts(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[list[CustomGptResponse]]:
    rows = GptsService(session).list_gpts(user)
    return ApiResponse.ok([CustomGptResponse.from_model(g) for g in rows])


@router.get("/{gpt_id}", response_model=ApiResponse[CustomGptResponse])
def get_gpt(
    gpt_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[CustomGptResponse]:
    g = GptsService(session).get_readable_gpt(gpt_id, user)
    return ApiResponse.ok(CustomGptResponse.from_model(g))


@router.put("/{gpt_id}", response_model=ApiResponse[CustomGptResponse])
def update_gpt(
    gpt_id: str,
    req: CustomGptUpdateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[CustomGptResponse]:
    g = GptsService(session).update_gpt(gpt_id, user, req)
    return ApiResponse.ok(CustomGptResponse.from_model(g))


@router.delete("/{gpt_id}", response_model=ApiResponse[None])
def delete_gpt(
    gpt_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[None]:
    GptsService(session).delete_gpt(gpt_id, user)
    return ApiResponse.ok(None)


# ── 세션 ──
@router.post(
    "/{gpt_id}/sessions",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[GptSessionResponse],
)
def create_session(
    gpt_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[GptSessionResponse]:
    s = GptsService(session).create_session(gpt_id, user)
    return ApiResponse.ok(GptSessionResponse.from_model(s))


@router.get("/{gpt_id}/sessions", response_model=ApiResponse[list[GptSessionResponse]])
def list_sessions(
    gpt_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[list[GptSessionResponse]]:
    rows = GptsService(session).list_sessions(gpt_id, user)
    return ApiResponse.ok([GptSessionResponse.from_model(s) for s in rows])


@router.patch("/{gpt_id}/sessions/{session_id}/name", response_model=ApiResponse[GptSessionResponse])
def rename_session(
    gpt_id: str,
    session_id: str,
    req: SessionRenameRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[GptSessionResponse]:
    s = GptsService(session).rename_session(gpt_id, session_id, user, req.name)
    return ApiResponse.ok(GptSessionResponse.from_model(s))


@router.delete("/{gpt_id}/sessions/{session_id}", response_model=ApiResponse[None])
def delete_session(
    gpt_id: str,
    session_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[None]:
    GptsService(session).delete_session(gpt_id, session_id, user)
    return ApiResponse.ok(None)


# ── 메시지 이력 ──
@router.get("/{gpt_id}/messages", response_model=ApiResponse[GptChatHistoryResponse])
def get_messages(
    gpt_id: str,
    session_id: str = Query(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[GptChatHistoryResponse]:
    msgs = GptsService(session).messages(gpt_id, session_id, user)
    return ApiResponse.ok(GptChatHistoryResponse(messages=msgs))


@router.delete("/{gpt_id}/messages", response_model=ApiResponse[None])
def clear_messages(
    gpt_id: str,
    session_id: str = Query(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[None]:
    GptsService(session).clear_messages(gpt_id, session_id, user)
    return ApiResponse.ok(None)


# ── 채팅 (SSE) ──
@router.post("/{gpt_id}/chat/stream")
def chat_stream(
    gpt_id: str,
    req: GptChatRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> StreamingResponse:
    """GPT 채팅 — 토큰 스트리밍(SSE). `data: {content, done, type?, title?}`."""
    stream = GptsService(session).stream_chat(
        gpt_id, user, req.session_id, req.messages, req.llm_resource_id
    )
    return StreamingResponse(stream, media_type="text/event-stream", headers=_SSE_HEADERS)
