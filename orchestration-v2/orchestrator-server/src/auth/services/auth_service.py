"""Authentication utilities — HS256 JWT 토큰 검증."""

import re
from datetime import UTC, datetime, timedelta
from typing import Optional

from jose import JWTError, jwt

from src.common.config import settings
from src.common.logging import logger
from src.auth.schemas.auth_schema import Token
from src.common.services.sanitization import sanitize_string


def create_access_token(
    thread_id: str,
    expires_delta: Optional[timedelta] = None,
    claims: Optional[dict] = None,
) -> Token:
    """Create a new HS256 access token.

    Args:
        thread_id: Subject (user ID or thread ID).
        expires_delta: Optional expiration override.
        claims: Optional additional claims.

    Returns:
        Token: The generated access token.
    """
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )

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


def verify_token(token: str) -> Optional[dict]:
    """HS256 JWT를 검증하고 payload를 반환한다.

    Args:
        token: Bearer 토큰 문자열.

    Returns:
        Optional[dict]: payload 또는 None.

    Raises:
        ValueError: 토큰 형식이 유효하지 않을 때.
    """
    if not token or not isinstance(token, str):
        raise ValueError("Token must be a non-empty string")

    if not re.match(r"^[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+$", token):
        raise ValueError("Token format is invalid - expected JWT format")

    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        thread_id: str = payload.get("sub")
        if thread_id is None:
            logger.warning("token_missing_sub")
            return None
        logger.info("token_verified", thread_id=thread_id)
        return payload
    except JWTError as e:
        logger.error("token_verification_failed", error=str(e))
        return None
