"""chat 도메인 라우터 (ADR-0008).

- 메시지 전송·승인 재개는 SSE(text/event-stream) 스트림.
- 승인(HITL) 메커니즘은 ADR-0008 참고.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlmodel import Session

from src.core.db import get_session
from src.core.response import ApiResponse
from src.domains.auth.dependencies import get_current_user
from src.domains.chat.schema import (
    ApprovalResumeRequest,
    MessageRequest,
    MessageResponse,
    SessionCreateRequest,
    SessionRenameRequest,
    SessionResponse,
)
from src.domains.chat.service import ChatService
from src.domains.user.model import User

router = APIRouter()

_SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


@router.post("/sessions", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[SessionResponse])
def create_session(
    req: SessionCreateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[SessionResponse]:
    s = ChatService(session).create_session(user, req.title)
    return ApiResponse.ok(SessionResponse.from_model(s))


@router.get("/sessions", response_model=ApiResponse[list[SessionResponse]])
def list_sessions(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[list[SessionResponse]]:
    rows = ChatService(session).list_sessions(user)
    return ApiResponse.ok([SessionResponse.from_model(s) for s in rows])


@router.patch("/sessions/{session_id}", response_model=ApiResponse[SessionResponse])
def rename_session(
    session_id: int,
    req: SessionRenameRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[SessionResponse]:
    s = ChatService(session).rename_session(session_id, user, req.title)
    return ApiResponse.ok(SessionResponse.from_model(s))


@router.delete("/sessions/{session_id}", response_model=ApiResponse[None])
def delete_session(
    session_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[None]:
    ChatService(session).delete_session(session_id, user)
    return ApiResponse.ok(None)


@router.get("/sessions/{session_id}/messages", response_model=ApiResponse[list[MessageResponse]])
def get_messages(
    session_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[list[MessageResponse]]:
    svc = ChatService(session)
    rows = svc.messages(session_id, user)
    att_map = svc.attachments_for([m.id for m in rows])
    return ApiResponse.ok([MessageResponse.from_model(m, att_map.get(m.id)) for m in rows])


@router.post("/sessions/{session_id}/messages")
def send_message(
    session_id: int,
    req: MessageRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> StreamingResponse:
    """메시지 전송. CONFIRM 도구를 만나면 `event: approval_required`를 내고 스트림을 닫는다."""
    stream = ChatService(session).stream_message(
        session_id, user, req.content, req.llm_resource_id, req.rag_group, req.files
    )
    return StreamingResponse(stream, media_type="text/event-stream", headers=_SSE_HEADERS)


@router.delete("/memory", response_model=ApiResponse[None])
def delete_memory(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[None]:
    """현재 사용자의 모든 장기 메모리 삭제 (ADR-0015)."""
    ChatService(session).delete_memory(user)
    return ApiResponse.ok(None)


@router.get("/attachments/{attachment_id}")
def download_attachment(
    attachment_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> FileResponse:
    """첨부 다운로드 — 소유자 또는 관리자 (ADR-0014 §4)."""
    path, filename, content_type = ChatService(session).download_attachment(user, attachment_id)
    return FileResponse(path=str(path), filename=filename, media_type=content_type)


@router.post("/sessions/{session_id}/approvals")
def submit_approvals(
    session_id: int,
    req: ApprovalResumeRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> StreamingResponse:
    """승인/거부 결정을 제출하고 그래프 실행을 이어서 스트림한다(ADR-0008 §4)."""
    stream = ChatService(session).resume(session_id, user, req.group_key, req.decisions)
    return StreamingResponse(stream, media_type="text/event-stream", headers=_SSE_HEADERS)
