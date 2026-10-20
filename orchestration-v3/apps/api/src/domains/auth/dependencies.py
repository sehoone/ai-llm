"""인증 의존성.

로그인·토큰 발급은 사내 IdP가 소유(ADR-0003). 이 모듈은 요청 보호용 FastAPI 의존성만 제공.
인증 우선순위:
  1. API 키 (sk- 접두사) — 프로그램 접근
  2. OIDC Bearer 토큰 (IdP 발급, JWKS 검증)
"""

from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from src.core.db import get_session
from src.core.security import verify_token
from src.domains.api_key.repository import ApiKeyRepository
from src.domains.auth.service import provision_user
from src.domains.user.model import User, UserRole
from src.domains.user.repository import UserRepository

_bearer = HTTPBearer()


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

    # 2) OIDC Bearer 토큰 → JIT 프로비저닝
    try:
        claims = verify_token(token)
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    return provision_user(session, claims)


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role not in (UserRole.ADMIN, UserRole.SUPERADMIN):
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user


def require_superadmin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.SUPERADMIN:
        raise HTTPException(status_code=403, detail="Superadmin privileges required")
    return user
