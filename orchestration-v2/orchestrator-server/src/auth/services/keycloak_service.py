"""Keycloak JWT validation service.

RS256 서명 검증, JWKS 공개키 캐싱(TTL 기반 + kid mismatch 시 즉시 갱신)을 담당.
python-jose[cryptography] 라이브러리를 사용한다.
"""

import time
from typing import Optional

import httpx
from jose import JWTError, jwt

from src.common.config import settings
from src.common.logging import logger

_jwks_cache: dict = {}
_jwks_fetched_at: float = 0.0


async def _fetch_jwks(force: bool = False) -> dict:
    """Keycloak JWKS 엔드포인트에서 공개키 목록을 가져온다.

    Args:
        force: True이면 캐시 TTL을 무시하고 즉시 갱신.

    Returns:
        dict: JWKS JSON { "keys": [...] }
    """
    global _jwks_cache, _jwks_fetched_at
    now = time.monotonic()
    if not force and _jwks_cache and (now - _jwks_fetched_at) < settings.KEYCLOAK_JWKS_CACHE_TTL:
        return _jwks_cache

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(settings.keycloak_jwks_url)
            response.raise_for_status()
            _jwks_cache = response.json()
            _jwks_fetched_at = time.monotonic()
            logger.info("keycloak_jwks_refreshed", keys=len(_jwks_cache.get("keys", [])))
            return _jwks_cache
    except httpx.HTTPError as e:
        logger.error("keycloak_jwks_fetch_failed", error=str(e), url=settings.keycloak_jwks_url)
        if _jwks_cache:
            logger.warning("keycloak_jwks_using_stale_cache")
            return _jwks_cache
        raise


def _find_key(jwks: dict, kid: Optional[str]) -> Optional[dict]:
    """JWKS에서 kid와 일치하는 키를 반환한다."""
    for key in jwks.get("keys", []):
        if kid is None or key.get("kid") == kid:
            return key
    return None


async def verify_keycloak_token(token: str) -> Optional[dict]:
    """Keycloak이 발급한 RS256 JWT를 검증하고 payload를 반환한다.

    1. JWT 헤더에서 kid 추출
    2. JWKS 캐시에서 해당 공개키 탐색 (miss 시 즉시 갱신)
    3. RS256 서명 + iss + exp 검증
    4. 성공 시 payload dict 반환, 실패 시 None

    Args:
        token: Bearer 토큰 문자열 (헤더 제외).

    Returns:
        Optional[dict]: 검증된 JWT payload, 또는 None.
    """
    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")

        jwks = await _fetch_jwks()
        key = _find_key(jwks, kid)

        if key is None:
            # kid를 찾지 못하면 JWKS를 강제 갱신 후 재시도 (키 로테이션 대응)
            logger.info("keycloak_jwks_kid_miss_refreshing", kid=kid)
            jwks = await _fetch_jwks(force=True)
            key = _find_key(jwks, kid)

        if key is None:
            logger.warning("keycloak_jwks_key_not_found", kid=kid)
            return None

        decode_options: dict = {"verify_aud": False}
        decode_kwargs: dict = {
            "algorithms": ["RS256"],
            "issuer": settings.keycloak_issuer,
            "options": decode_options,
        }
        if settings.KEYCLOAK_TOKEN_AUDIENCE:
            decode_options["verify_aud"] = True
            decode_kwargs["audience"] = settings.KEYCLOAK_TOKEN_AUDIENCE

        payload = jwt.decode(token, key, **decode_kwargs)
        logger.info("keycloak_token_verified", sub=payload.get("sub"), email=payload.get("email"))
        return payload

    except JWTError as e:
        logger.warning("keycloak_token_verification_failed", error=str(e))
        return None
    except Exception as e:
        logger.error("keycloak_token_unexpected_error", error=str(e), exc_info=True)
        return None
