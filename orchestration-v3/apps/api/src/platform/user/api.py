from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from src.core.db import get_session
from src.core.response import ApiResponse
from src.platform.auth.dependencies import get_current_user, require_admin, require_superadmin
from src.platform.user.model import User
from src.platform.user.schema import (
    AdminUserUpdateRequest,
    UserCreateRequest,
    UserResponse,
    UserUpdateRequest,
)
from src.platform.user.service import UserService

router = APIRouter()


@router.post("", response_model=ApiResponse[UserResponse], status_code=201)
def create_user(
    req: UserCreateRequest,
    _: User = Depends(require_admin),
    session: Session = Depends(get_session),
) -> ApiResponse[UserResponse]:
    user = UserService(session).create(req)
    return ApiResponse.ok(UserResponse.model_validate(user), message="사용자가 생성되었습니다.")


@router.get("/me", response_model=ApiResponse[UserResponse])
def get_me(current: User = Depends(get_current_user)) -> ApiResponse[UserResponse]:
    return ApiResponse.ok(UserResponse.model_validate(current))


@router.patch("/me", response_model=ApiResponse[UserResponse])
def update_me(
    req: UserUpdateRequest,
    current: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[UserResponse]:
    user = UserService(session).update_me(current.id, req)
    return ApiResponse.ok(UserResponse.model_validate(user))


@router.get("", response_model=ApiResponse[list[UserResponse]])
def list_users(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _: User = Depends(require_admin),
    session: Session = Depends(get_session),
) -> ApiResponse[list[UserResponse]]:
    users = UserService(session).list(limit=limit, offset=offset)
    return ApiResponse.ok([UserResponse.model_validate(u) for u in users])


@router.get("/{user_id}", response_model=ApiResponse[UserResponse])
def get_user(
    user_id: int,
    _: User = Depends(require_admin),
    session: Session = Depends(get_session),
) -> ApiResponse[UserResponse]:
    user = UserService(session).get(user_id)
    return ApiResponse.ok(UserResponse.model_validate(user))


@router.patch("/{user_id}", response_model=ApiResponse[UserResponse])
def admin_update_user(
    user_id: int,
    req: AdminUserUpdateRequest,
    _: User = Depends(require_admin),
    session: Session = Depends(get_session),
) -> ApiResponse[UserResponse]:
    user = UserService(session).admin_update(user_id, req)
    return ApiResponse.ok(UserResponse.model_validate(user))


@router.delete("/{user_id}", response_model=ApiResponse[None])
def deactivate_user(
    user_id: int,
    _: User = Depends(require_superadmin),
    session: Session = Depends(get_session),
) -> ApiResponse[None]:
    UserService(session).deactivate(user_id)
    return ApiResponse.ok(message="사용자가 비활성화되었습니다.")
