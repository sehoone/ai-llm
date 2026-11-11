"""chat 도메인 라우터 (ADR-0008).

- 메시지 전송·승인 재개는 SSE(text/event-stream) 스트림.
- 승인(HITL) 메커니즘은 ADR-0008 참고.
"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from src.core.db import get_session
from src.core.response import ApiResponse
from src.platform.auth.dependencies import get_current_user, require_admin
from src.domains.chat.schema import (
    ApprovalResumeRequest,
    ChatHistoryItem,
    ChatHistoryListResponse,
    MessageRequest,
    MessageResponse,
    SessionCreateRequest,
    SessionRenameRequest,
    SessionResponse,
)
from src.domains.chat.service import ChatService
from src.platform.user.model import User

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
    svc = ChatService(session)
    svc.validate_files(req.files)  # 스트림 시작 전 검증 → 깔끔한 400 (ADR-0016 §5)
    stream = svc.stream_message(
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


# ── 대화 이력(관리자 뷰) ──
# `/history/all`을 `/history/{message_id}`보다 먼저 선언 — 경로 매칭 우선순위.
@router.get("/history/all", response_model=ApiResponse[ChatHistoryListResponse])
def all_chat_history(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: str = "",
    _admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
) -> ApiResponse[ChatHistoryListResponse]:
    """전체 사용자 대화 이력(질문·답변 페어) — 페이지네이션·검색. 관리자 전용."""
    return ApiResponse.ok(ChatService(session).all_history(limit, offset, search))


@router.get("/history/{message_id}", response_model=ApiResponse[ChatHistoryItem])
def chat_history_detail(
    message_id: int,
    _admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
) -> ApiResponse[ChatHistoryItem]:
    """대화 이력 상세(첨부 메타 포함). 관리자 전용."""
    return ApiResponse.ok(ChatService(session).history_detail(message_id))


@router.get("/attachments/{attachment_id}")
def download_attachment(
    attachment_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> StreamingResponse:
    """첨부 다운로드 — 소유자 또는 관리자 (ADR-0014 §4). MinIO 객체를 프록시 스트림(ADR-0017 §4)."""
    stream, filename, content_type = ChatService(session).download_attachment(user, attachment_id)
    disposition = f"attachment; filename*=UTF-8''{quote(filename)}"
    return StreamingResponse(
        stream, media_type=content_type, headers={"Content-Disposition": disposition}
    )


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
