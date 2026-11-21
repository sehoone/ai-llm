"""connector 도메인 라우터 (ADR-0022) — 사내 MCP 서버 등록 CRUD + 도구 미리보기.

응답은 `ApiResponse[T]`. sk- 키 값은 반환하지 않는다(has_credential bool만).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from src.core.db import get_session
from src.core.response import ApiResponse
from src.domains.auth.dependencies import get_current_user
from src.domains.connector.schema import (
    ConnectorCreateRequest,
    ConnectorResponse,
    ConnectorToolItem,
    ConnectorUpdateRequest,
)
from src.domains.connector.service import ConnectorService
from src.domains.user.model import User

router = APIRouter()


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[ConnectorResponse])
def create_connector(
    req: ConnectorCreateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[ConnectorResponse]:
    c = ConnectorService(session).create(user, req)
    return ApiResponse.ok(ConnectorResponse.from_model(c))


@router.get("/", response_model=ApiResponse[list[ConnectorResponse]])
def list_connectors(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[list[ConnectorResponse]]:
    rows = ConnectorService(session).list_connectors(user)
    return ApiResponse.ok([ConnectorResponse.from_model(c) for c in rows])


@router.get("/{connector_id}", response_model=ApiResponse[ConnectorResponse])
def get_connector(
    connector_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[ConnectorResponse]:
    c = ConnectorService(session).get_owned(connector_id, user)
    return ApiResponse.ok(ConnectorResponse.from_model(c))


@router.put("/{connector_id}", response_model=ApiResponse[ConnectorResponse])
def update_connector(
    connector_id: str,
    req: ConnectorUpdateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[ConnectorResponse]:
    c = ConnectorService(session).update(connector_id, user, req)
    return ApiResponse.ok(ConnectorResponse.from_model(c))


@router.delete("/{connector_id}", response_model=ApiResponse[None])
def delete_connector(
    connector_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[None]:
    ConnectorService(session).delete(connector_id, user)
    return ApiResponse.ok(None)


@router.get("/{connector_id}/tools", response_model=ApiResponse[list[ConnectorToolItem]])
def preview_tools(
    connector_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[list[ConnectorToolItem]]:
    """커넥터가 노출하는 MCP 도구 미리보기. MCP 클라이언트 미설치/연결 실패 시 빈 목록."""
    items = ConnectorService(session).preview_tools(connector_id, user)
    return ApiResponse.ok([ConnectorToolItem(**it) for it in items])
