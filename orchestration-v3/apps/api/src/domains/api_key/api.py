from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from src.core.db import get_session
from src.core.response import ApiResponse
from src.domains.api_key.schema import ApiKeyCreateRequest, ApiKeyResponse
from src.domains.api_key.service import ApiKeyService
from src.domains.auth.dependencies import get_current_user
from src.domains.user.model import User

router = APIRouter()


@router.get("", response_model=ApiResponse[list[ApiKeyResponse]])
def list_api_keys(
    current: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[list[ApiKeyResponse]]:
    return ApiResponse.ok(ApiKeyService(session).list(current.id))


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[ApiKeyResponse])
def create_api_key(
    req: ApiKeyCreateRequest,
    current: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[ApiKeyResponse]:
    return ApiResponse.ok(ApiKeyService(session).create(current.id, req))


@router.delete("/{key_id}", response_model=ApiResponse[None])
def revoke_api_key(
    key_id: int,
    current: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[None]:
    ApiKeyService(session).revoke(current.id, key_id)
    return ApiResponse.ok(message="API 키가 폐기되었습니다.")
