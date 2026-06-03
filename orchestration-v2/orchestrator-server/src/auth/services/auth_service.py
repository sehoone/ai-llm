"""Authentication utilities — HS256(jwt mode) 또는 RS256(keycloak mode) 토큰 검증."""

import re
from datetime import (
    UTC,
    datetime,
    timedelta,
)
from typing import Optional

from jose import (
    JWTError,
    jwt,
)

from src.common.config import settings
from src.common.logging import logger
from src.auth.schemas.auth_schema import Token
from src.common.services.sanitization import sanitize_string


def create_access_token(
    thread_id: str,
    expires_delta: Optional[timedelta] = None,
    claims: Optional[dict] = None
) -> Token:
    """Create a new HS256 access token for a thread or user.

    Args:
        thread_id: The unique thread ID (or user ID) for the subject.
        expires_delta: Optional expiration time delta.
        claims: Optional additional claims to include in the token.

    Returns:
        Token: The generated access token.
    """
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "sub": str(thread_id),
        "exp": expire,
        "iat": datetime.now(UTC),
        "jti": sanitize_string(f"{thread_id}-{datetime.now(UTC).timestamp()}"),
    }

    if claims:
        to_encode.update(claims)

    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    logger.info("token_created", thread_id=thread_id, expires_at=expire.isoformat())

    return Token(access_token=encoded_jwt, expires_at=expire)


def _verify_hs256_token(token: str) -> Optional[dict]:
    """HS256 서명의 JWT를 검증한다 (jwt 모드 전용)."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        thread_id: str = payload.get("sub")
        if thread_id is None:
            logger.warning("token_missing_thread_id")
            return None
        logger.info("hs256_token_verified", thread_id=thread_id)
        return payload
    except JWTError as e:
        logger.error("hs256_token_verification_failed", error=str(e))
        return None


def verify_token(token: str) -> Optional[dict]:
    """JWT 토큰을 검증하고 payload를 반환한다.

    AUTH_MODE 환경변수에 따라 검증 방식이 결정된다.
    - "keycloak": Keycloak RS256 검증 (keycloak_service.verify_keycloak_token 위임)
    - "jwt"(기본값): 공유 비밀키 HS256 검증

    keycloak 모드에서는 호출자가 async 컨텍스트여야 하므로 None을 반환한다.
    실제 Keycloak 검증은 auth_api.get_current_user에서 직접 await 처리한다.

    Args:
        token: Bearer 토큰 문자열.

    Returns:
        Optional[dict]: payload 또는 None.

    Raises:
        ValueError: 토큰 형식이 유효하지 않을 때.
    """
    if not token or not isinstance(token, str):
        logger.warning("token_invalid_format")
        raise ValueError("Token must be a non-empty string")

    if not re.match(r"^[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+$", token):
        logger.warning("token_suspicious_format")
        raise ValueError("Token format is invalid - expected JWT format")

    if settings.AUTH_MODE == "keycloak":
        # Keycloak 모드에서는 async 검증이 필요하므로 None 반환
        # → auth_api.get_current_user에서 await keycloak_service.verify_keycloak_token() 호출
        return None

    return _verify_hs256_token(token)
