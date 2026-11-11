"""인증 라우터 — ID/PW 로그인 + 비밀번호 변경.

백엔드가 자격을 직접 검증하고 HS256 JWT를 발급한다(ADR-0003 전환).
토큰 subject는 로컬 user id이며, role·username·email을 클레임으로 담아 프론트 표시에 쓴다.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from src.core.db import get_session
from src.core.response import ApiResponse
from src.core.security import create_access_token, hash_password, verify_password
from src.platform.auth.dependencies import get_current_user
from src.platform.auth.schema import LoginRequest, LoginResponse, PasswordChangeRequest
from src.platform.auth.service import authenticate
from src.platform.user.model import User
from src.platform.user.repository import UserRepository
from src.platform.user.schema import UserResponse

router = APIRouter()


@router.post("/login", response_model=ApiResponse[LoginResponse])
def login(
    req: LoginRequest,
    session: Session = Depends(get_session),
) -> ApiResponse[LoginResponse]:
    user = authenticate(session, req.username, req.password)
    if user is None:
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")

    token = create_access_token(
        subject=str(user.id),
        claims={
            "preferred_username": user.username,
            "email": user.email,
            "roles": [user.role.value],
        },
    )
    return ApiResponse.ok(
        LoginResponse(access_token=token, user=UserResponse.model_validate(user))
    )


@router.post("/password", response_model=ApiResponse[None])
def change_password(
    req: PasswordChangeRequest,
    current: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[None]:
    if not current.hashed_password or not verify_password(
        req.current_password, current.hashed_password
    ):
        raise HTTPException(status_code=400, detail="현재 비밀번호가 올바르지 않습니다.")
    current.hashed_password = hash_password(req.new_password)
    UserRepository(session).save(current)
    return ApiResponse.ok(message="비밀번호가 변경되었습니다.")
