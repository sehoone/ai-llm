from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from src.core.db import get_session
from src.core.response import ApiResponse
from src.domains.auth.dependencies import get_current_user, require_admin
from src.domains.llm_resource.schema import (
    ChatModelResponse,
    LlmResourceCreateRequest,
    LlmResourceResponse,
    LlmResourceUpdateRequest,
)
from src.domains.llm_resource.service import LlmResourceService
from src.domains.user.model import User

router = APIRouter()


@router.get("/chat-models", response_model=ApiResponse[list[ChatModelResponse]])
def get_chat_models(
    _: User = Depends(get_current_user),  # 인증된 사용자 (에이전트 모델 선택용)
    session: Session = Depends(get_session),
) -> ApiResponse[list[ChatModelResponse]]:
    return ApiResponse.ok(LlmResourceService(session).chat_models())


@router.get("", response_model=ApiResponse[list[LlmResourceResponse]])
def list_resources(
    type: str | None = Query(default=None),
    _: User = Depends(require_admin),
    session: Session = Depends(get_session),
) -> ApiResponse[list[LlmResourceResponse]]:
    return ApiResponse.ok(LlmResourceService(session).list(type))


@router.get("/{resource_id}", response_model=ApiResponse[LlmResourceResponse])
def get_resource(
    resource_id: int,
    _: User = Depends(require_admin),
    session: Session = Depends(get_session),
) -> ApiResponse[LlmResourceResponse]:
    return ApiResponse.ok(LlmResourceService(session).get(resource_id))


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[LlmResourceResponse])
def create_resource(
    req: LlmResourceCreateRequest,
    _: User = Depends(require_admin),
    session: Session = Depends(get_session),
) -> ApiResponse[LlmResourceResponse]:
    return ApiResponse.ok(LlmResourceService(session).create(req))


@router.patch("/{resource_id}", response_model=ApiResponse[LlmResourceResponse])
def update_resource(
    resource_id: int,
    req: LlmResourceUpdateRequest,
    _: User = Depends(require_admin),
    session: Session = Depends(get_session),
) -> ApiResponse[LlmResourceResponse]:
    return ApiResponse.ok(LlmResourceService(session).update(resource_id, req))


@router.patch("/{resource_id}/toggle", response_model=ApiResponse[LlmResourceResponse])
def toggle_resource(
    resource_id: int,
    _: User = Depends(require_admin),
    session: Session = Depends(get_session),
) -> ApiResponse[LlmResourceResponse]:
    return ApiResponse.ok(LlmResourceService(session).toggle_active(resource_id))


@router.delete("/{resource_id}", response_model=ApiResponse[None])
def delete_resource(
    resource_id: int,
    _: User = Depends(require_admin),
    session: Session = Depends(get_session),
) -> ApiResponse[None]:
    LlmResourceService(session).delete(resource_id)
    return ApiResponse.ok(message="LLM 리소스가 삭제되었습니다.")
