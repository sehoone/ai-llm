"""인증 의존성 — 요청 보호용 FastAPI 의존성.

인증 우선순위:
  1. API 키 (sk- 접두사) — 프로그램 접근
  2. 자체 발급 Bearer 토큰 (ID/PW 로그인 → HS256 JWT, subject = 로컬 user id)
"""

from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from src.core.db import get_session
from src.core.security import decode_access_token
from src.platform.api_key.repository import ApiKeyRepository
from src.platform.user.model import User, UserRole
from src.platform.user.repository import UserRepository

_bearer = HTTPBearer()

_INVALID_CREDS = HTTPException(
    status_code=401,
    detail="Invalid authentication credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    session: Session = Depends(get_session),
) -> User:
    token = credentials.credentials

    # 1) API 키
    if token.startswith("sk-"):
        api_key = ApiKeyRepository(session).get_by_key(token)
        if api_key is None or not api_key.is_active or api_key.is_expired():
            raise HTTPException(status_code=401, detail="Invalid API Key")
        user = UserRepository(session).get(api_key.user_id)
        if user is None:
            raise HTTPException(status_code=401, detail="User for API key not found")
        return user

    # 2) 자체 발급 JWT → 로컬 user 조회
    try:
        claims = decode_access_token(token)
        user_id = int(claims["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as e:
        raise _INVALID_CREDS from e

    user = UserRepository(session).get(user_id)
    if user is None or user.status != "active":
        raise _INVALID_CREDS
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role not in (UserRole.ADMIN, UserRole.SUPERADMIN):
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user


def require_superadmin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.SUPERADMIN:
        raise HTTPException(status_code=403, detail="Superadmin privileges required")
    return user
