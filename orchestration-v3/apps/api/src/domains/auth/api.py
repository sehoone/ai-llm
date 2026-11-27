"""인증 라우터 — ID/PW 로그인 + 비밀번호 변경.

백엔드가 자격을 직접 검증하고 HS256 JWT를 발급한다(ADR-0003 전환).
토큰 subject는 로컬 user id이며, role·username·email을 클레임으로 담아 프론트 표시에 쓴다.
"""

from datetime import UTC, datetime

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from src.core.db import get_session
from src.core.response import ApiResponse
from src.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from src.domains.auth.dependencies import get_current_user
from src.domains.auth.repository import RevokedTokenRepository
from src.domains.auth.schema import (
    LoginRequest,
    LoginResponse,
    PasswordChangeRequest,
    RegisterRequest,
)
from src.domains.auth.service import authenticate, register
from src.domains.user.model import User
from src.domains.user.repository import UserRepository
from src.domains.user.schema import UserResponse

router = APIRouter()
_bearer = HTTPBearer()


def _issue_login(user: User) -> ApiResponse[LoginResponse]:
    """user → JWT 발급 + LoginResponse. 토큰 subject는 로컬 user id, 클레임은 프론트 표시용."""
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


# 레이트리밋은 nginx limit_req(zone=login)로 이전 (ADR-0032 Phase 2)
@router.post("/login", response_model=ApiResponse[LoginResponse])
def login(
    req: LoginRequest,
    session: Session = Depends(get_session),
) -> ApiResponse[LoginResponse]:
    user = authenticate(session, req.username, req.password)
    if user is None:
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")
    return _issue_login(user)


# 레이트리밋은 nginx limit_req(zone=register)로 이전 (ADR-0032 Phase 2)
@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[LoginResponse],
)
def register_user(
    req: RegisterRequest,
    session: Session = Depends(get_session),
) -> ApiResponse[LoginResponse]:
    """사용자 셀프 가입(ADR-0020) — role=USER 생성 후 즉시 로그인 토큰 발급."""
    user = register(session, req.username, req.email, req.password)
    return _issue_login(user)


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


@router.post("/logout", response_model=ApiResponse[None])
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    session: Session = Depends(get_session),
) -> ApiResponse[None]:
    """현재 JWT를 폐기(블랙리스트 등록) — 만료 전이라도 이후 인증을 차단 (ADR-0032 Phase 2).

    API 키(sk-)는 로그아웃 대상이 아니다(활성/만료로 관리). 토큰이 유효하지 않으면 멱등하게 ok.
    """
    token = credentials.credentials
    if token.startswith("sk-"):
        raise HTTPException(status_code=400, detail="API 키는 로그아웃 대상이 아닙니다.")
    try:
        claims = decode_access_token(token)
    except jwt.PyJWTError:
        return ApiResponse.ok(message="로그아웃되었습니다.")  # 이미 무효 — 멱등
    jti, sub, exp = claims.get("jti"), claims.get("sub"), claims.get("exp")
    if jti and sub and exp:
        expires_at = datetime.fromtimestamp(exp, tz=UTC).replace(tzinfo=None)
        RevokedTokenRepository(session).revoke(jti, int(sub), expires_at)
    return ApiResponse.ok(message="로그아웃되었습니다.")
